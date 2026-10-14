from pathlib import Path
import subprocess,json,time
R=Path(__file__).resolve().parent
P=str(R/'.venv/bin/python')
def run(name,**kwargs):
    cmd=[P,str(R/'experiment.py'),'--name',name]
    for k,v in kwargs.items():
        cmd+=['--'+k.replace('_','-')]+([] if v is True else [str(v)])
    if (R/'runs'/name/'result.json').exists():return json.loads((R/'runs'/name/'result.json').read_text())
    print('START',name,flush=True)
    subprocess.run(cmd,check=True,cwd=R)
    return json.loads((R/'runs'/name/'result.json').read_text())
pilots=[]
for lr in [.0003,.001,.003,.01]:
    result=run(f'lr-pilot-{lr:g}',lr=lr,tokens=8192000)
    if result['status']=='completed':pilots.append((result['val_loss'],lr))
for lr in [.03,.1,1.]:
    result=run(f'lr-stability-{lr:g}',lr=lr,tokens=4096000)
    if result['status']=='diverged':break
# Confirm the best two pilot candidates at the full Apple Silicon budget.
full=[]
for _,lr in sorted(pilots)[:2]:
    if lr==.001:
        r=json.loads((R/'runs/baseline-40m/evaluation.json').read_text());full.append((r['val_loss'],lr,'baseline-40m'))
    else:
        name=f'lr-full-{lr:g}';r=run(name,lr=lr);full.append((r['full_val_loss'],lr,name))
# Include the existing 1e-3 baseline in the final selection.
r=json.loads((R/'runs/baseline-40m/evaluation.json').read_text());full.append((r['val_loss'],.001,'baseline-40m'))
_,best,reference=min(full)
(R/'selection.json').write_text(json.dumps(dict(pilots=pilots,full=full,best_lr=best,reference=reference),indent=2))
for variant in ['no_norm','post_norm','nope','silu']:
    run('ablation-'+variant,lr=best,variant=variant)
run('ablation-no_norm-lower',lr=best/10,variant='no_norm')
# A matched-initialization control for the weight-tying modification.
for variant in ['untied_small_init','tied']:run('custom-'+variant,lr=best,variant=variant)
# Probe maximum feasible physical batch under a 24 GiB process allocation budget.
max_batch=128
for batch in [128,256,512,1024]:
    r=run(f'batch-probe-{batch}',batch=batch,probe=True)
    if r['status']!='completed':break
    max_batch=batch
# Equal 4.096M-token budget including batch=1; record the different update counts.
for batch in sorted(set([1,32,64,128,max_batch])):
    run(f'batch-{batch}',lr=best,batch=batch,tokens=4096000)
# Wait only for the independent CPU data-preparation process, then run OWT.
while not (R/'owt/manifest.json').exists():
    if (R/'owt/FAILED').exists():raise RuntimeError('OWT preparation failed')
    print('WAIT OWT preparation',flush=True);time.sleep(30)
run('owt-baseline',lr=best,dataset='owt')
(R/'SUITE_DONE.json').write_text(json.dumps(dict(best_lr=best,reference=reference,max_batch=max_batch)))
print('SUITE DONE',flush=True)
