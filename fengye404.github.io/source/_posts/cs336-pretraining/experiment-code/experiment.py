"""One isolated, resumable experiment. Execute on Mac Studio only."""
from pathlib import Path
import argparse,json,math,time,types,hashlib
import numpy as np
import torch
from model import TransformerLM,Linear,silu
from training import AdamW,cross_entropy,cosine_lr,clip_gradients,get_batch,generate
from tokenizer import Tokenizer
ROOT=Path(__file__).resolve().parent

def post_forward(self,x,token_positions=None):
    x=self.norm1(x+self.attention(x,token_positions))
    return self.norm2(x+self.ffn(x))
class FFNSiLU(torch.nn.Module):
    def __init__(self):
        super().__init__();self.w1=Linear(512,2048,'mps',torch.float32);self.w2=Linear(2048,512,'mps',torch.float32)
    def forward(self,x):return self.w2(silu(self.w1(x)))
def build(variant):
    torch.manual_seed(42)
    model=TransformerLM(10000,4,512,16,1344,theta=10000,max_seq_len=256,device='mps',dtype=torch.float32)
    for b in model.layers:
        if variant=='no_norm':b.norm1=torch.nn.Identity();b.norm2=torch.nn.Identity()
        if variant=='post_norm':b.forward=types.MethodType(post_forward,b)
        if variant=='nope':b.attention.rope=None
        if variant=='silu':b.ffn=FFNSiLU()
    if variant=='no_norm':model.norm=torch.nn.Identity()
    if variant in ['tied','untied_small_init']:
        torch.nn.init.normal_(model.token_embedding.embedding,std=.02)
        if variant=='tied':model.linear.W=model.token_embedding.embedding
        else:
            with torch.no_grad():model.linear.W.copy_(model.token_embedding.embedding)
    return model

def main():
    a=argparse.ArgumentParser();a.add_argument('--name',required=True);a.add_argument('--lr',type=float,default=.001);a.add_argument('--batch',type=int,default=32);a.add_argument('--tokens',type=int,default=40960000);a.add_argument('--variant',default='baseline');a.add_argument('--dataset',default='tiny');a.add_argument('--probe',action='store_true');args=a.parse_args()
    # Limit this process to 24 GiB so batch probing cannot consume the whole shared machine.
    torch.mps.set_per_process_memory_fraction(24*1024**3/torch.mps.recommended_max_memory())
    out=ROOT/'runs'/args.name;out.mkdir(exist_ok=True,parents=True)
    if (out/'result.json').exists():print('EXISTS',args.name,flush=True);return
    cfg=vars(args)|{'steps':args.tokens//(args.batch*256),'seed':42,'warmup_fraction':.02,'context':256,'vocab':10000,'memory_budget_GiB':24}
    cfg['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['experiment.py','model.py','training.py','tokenizer.py']}
    (out/'config.json').write_text(json.dumps(cfg,indent=2))
    model=build(args.variant);optimizer=AdamW(model.parameters(),lr=args.lr)
    directory=ROOT/('data' if args.dataset=='tiny' else 'owt')
    train=np.memmap(directory/'train.bin',dtype=np.uint16,mode='r');valid=np.memmap(directory/'valid.bin',dtype=np.uint16,mode='r')
    rng=np.random.default_rng(42);steps=cfg['steps'];warmup=max(1,round(steps*.02));interval=max(1,steps//20)
    @torch.no_grad()
    def evaluate(full=False):
        model.eval();total=0.;count=0
        if full:
            n=(len(valid)-1)//256
            for first in range(0,n,32):
                starts=np.arange(first,min(first+32,n))*256
                x=torch.from_numpy(np.stack([valid[i:i+256] for i in starts]).astype(np.int64)).to('mps')
                y=torch.from_numpy(np.stack([valid[i+1:i+257] for i in starts]).astype(np.int64)).to('mps')
                total+=cross_entropy(model(x),y).item()*len(starts);count+=len(starts)
        else:
            vrng=np.random.default_rng(2026)
            for _ in range(20):
                x,y=get_batch(valid,32,256,'mps',vrng);total+=cross_entropy(model(x),y).item();count+=1
        model.train();return total/count
    start_step=0;previous_seconds=0.;resume=out/'resume.pt'
    if resume.exists():
        ck=torch.load(resume,map_location='cpu',weights_only=False)
        model.load_state_dict(ck['model']);optimizer.load_state_dict(ck['optimizer']);rng.bit_generator.state=ck['rng'];start_step=ck['step'];previous_seconds=ck['seconds'];del ck
    started=time.perf_counter();status='completed';reason=None;last_val=None;bad=0;completed=start_step
    try:
        with (out/'metrics.jsonl').open('a') as log:
            for step in range(start_step,3 if args.probe else steps):
                lr=cosine_lr(step,args.lr,args.lr*.1,warmup,steps)
                for g in optimizer.param_groups:g['lr']=lr
                x,y=get_batch(train,args.batch,256,'mps',rng);optimizer.zero_grad(set_to_none=True)
                loss=cross_entropy(model(x),y);loss.backward();norm=clip_gradients(model.parameters(),1.)
                value=loss.item()
                if args.name.startswith('lr-stability-') or (step+1)%10==0 or step<10:
                    observation=dict(step=step+1,tokens=(step+1)*args.batch*256,seconds=previous_seconds+time.perf_counter()-started,train_loss=value if math.isfinite(value) else None,val_loss=None,lr=lr,grad_norm=norm if math.isfinite(norm) else None)
                    log.write(json.dumps(observation)+'\n');log.flush()
                if not math.isfinite(value) or not math.isfinite(norm):
                    status='diverged';reason=f'nonfinite loss/gradient at step {step+1}';break
                optimizer.step();completed=step+1
                # Persist the actual finite explosion; do not label slower convergence as divergence.
                bad=bad+1 if value>50 else 0
                if bad>=10:status='diverged';reason='training loss > 50 for 10 consecutive steps';break
                if completed%interval==0 or completed==steps or args.probe:
                    last_val=evaluate() if not args.probe else None
                    r=dict(step=completed,tokens=completed*args.batch*256,seconds=previous_seconds+time.perf_counter()-started,train_loss=value,val_loss=last_val,lr=lr,grad_norm=norm,allocated_bytes=torch.mps.current_allocated_memory(),driver_bytes=torch.mps.driver_allocated_memory())
                    log.write(json.dumps(r)+'\n');log.flush();print(args.name,r,flush=True)
                if not args.probe and completed%max(interval,steps//4)==0:
                    torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),rng=rng.bit_generator.state,step=completed,seconds=previous_seconds+time.perf_counter()-started),out/'resume.tmp')
                    (out/'resume.tmp').replace(resume)
    except RuntimeError as e:
        if 'out of memory' in str(e).lower():status='memory_limit';reason=str(e)
        else:raise
    elapsed=previous_seconds+time.perf_counter()-started
    result=dict(name=args.name,status=status,reason=reason,steps=completed,tokens=completed*args.batch*256,seconds=elapsed,val_loss=last_val,parameters=sum(p.numel() for p in model.parameters()))
    if status=='completed' and not args.probe:
        torch.save({'model':model.state_dict(),'config':cfg},out/'model.pt')
        result['full_val_loss']=evaluate(full=True) if args.tokens>=40960000 else None
        payload=json.loads((ROOT/'tokenizer.json' if args.dataset=='tiny' else directory/'tokenizer.json').read_text())
        tok=Tokenizer({int(k):bytes.fromhex(v) for k,v in payload['vocab'].items()},[(bytes.fromhex(a),bytes.fromhex(b)) for a,b in payload['merges']],payload['special_tokens'])
        prompt='Once upon a time, there was a little girl named Lily.' if args.dataset=='tiny' else 'The future of technology depends on'
        samples=[]
        for temp in [0,.8]:
            torch.manual_seed(42);ids=generate(model,tok.encode(prompt),256,256,tok.encode('<|endoftext|>')[0],temp,.9)
            samples.append(dict(prompt=prompt,temperature=temp,top_p=.9,seed=42,text=tok.decode(ids),new_tokens=len(ids)-len(tok.encode(prompt))))
        (out/'samples.json').write_text(json.dumps(samples,indent=2))
    (out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False));print('RESULT',result,flush=True)
if __name__=='__main__':main()
