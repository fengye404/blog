from pathlib import Path
import json, time, math
import numpy as np
import torch
from model import TransformerLM
from training import AdamW,cross_entropy,cosine_lr,clip_gradients,get_batch,save_checkpoint,generate
from tokenizer import Tokenizer
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'runs/baseline-40m'
OUT.mkdir(parents=True,exist_ok=True)
cfg=dict(vocab_size=10000,num_layers=4,d_model=512,num_heads=16,d_ff=1344,context_length=256,batch_size=32,total_steps=5000,max_lr=.001,min_lr=.0001,warmup_steps=100,weight_decay=.1,betas=[.9,.95],max_norm=1.,seed=42,device='mps',dtype='float32',tokenizer_training_documents=10000)
(OUT/'config.json').write_text(json.dumps(cfg,indent=2))
torch.manual_seed(42)
model=TransformerLM(10000,4,512,16,1344,theta=10000,max_seq_len=256,device='mps',dtype=torch.float32)
optimizer=AdamW(model.parameters(),lr=cfg['max_lr'])
train_data=np.memmap(ROOT/'data/train.bin',dtype=np.uint16,mode='r')
val_data=np.memmap(ROOT/'data/valid.bin',dtype=np.uint16,mode='r')
rng=np.random.default_rng(42)
@torch.no_grad()
def evaluate():
    model.eval();r=np.random.default_rng(2026);values=[]
    for _ in range(20):
        x,y=get_batch(val_data,32,256,'mps',r)
        values.append(cross_entropy(model(x),y).item())
    model.train();return sum(values)/len(values)
started=time.perf_counter()
with (OUT/'metrics.jsonl').open('w') as log:
    for step in range(5000):
        lr=cosine_lr(step,.001,.0001,100,5000)
        for group in optimizer.param_groups: group['lr']=lr
        x,y=get_batch(train_data,32,256,'mps',rng)
        optimizer.zero_grad(set_to_none=True)
        loss=cross_entropy(model(x),y)
        loss.backward();norm=clip_gradients(model.parameters(),1)
        if not math.isfinite(norm):raise RuntimeError(f'nonfinite gradient at {step}')
        optimizer.step()
        if (step+1)%100==0:
            val=evaluate()
            rec=dict(step=step+1,tokens=(step+1)*8192,train_loss=loss.item(),val_loss=val,lr=lr,grad_norm=norm,seconds=time.perf_counter()-started)
            log.write(json.dumps(rec)+'\n');log.flush();print(rec,flush=True)
        if (step+1)%1000==0:
            save_checkpoint(OUT/f'step-{step+1}.pt',model,optimizer,step+1)
payload=json.loads((ROOT/'tokenizer.json').read_text())
tok=Tokenizer({int(k):bytes.fromhex(v) for k,v in payload['vocab'].items()},[(bytes.fromhex(a),bytes.fromhex(b)) for a,b in payload['merges']],payload['special_tokens'])
prompt='Once upon a time, there was a little girl named Lily.'
samples=[]
for temperature in [0,.8]:
    torch.manual_seed(42)
    ids=generate(model,tok.encode(prompt),256,256,tok.encode('<|endoftext|>')[0],temperature,.9)
    samples.append(dict(prompt=prompt,temperature=temperature,top_p=.9,seed=42,text=tok.decode(ids)))
(OUT/'samples.json').write_text(json.dumps(samples,indent=2,ensure_ascii=False))
(OUT/'DONE.json').write_text(json.dumps(dict(seconds=time.perf_counter()-started,steps=5000)))
print('DONE',flush=True)
