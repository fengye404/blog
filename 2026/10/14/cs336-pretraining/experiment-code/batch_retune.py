"""Follow the suite with learning-rate checks; never train concurrently."""
from pathlib import Path
import subprocess,time,json
R=Path(__file__).resolve().parent
while not (R/'SUITE_DONE.json').exists():time.sleep(10)
for batch,lr in [(1,.0005),(64,.0042),(128,.006)]:
    name=f'batch-{batch}-retuned'
    subprocess.run([str(R/'.venv/bin/python'),'-u',str(R/'experiment.py'),'--name',name,'--batch',str(batch),'--lr',str(lr),'--tokens','4096000'],check=True,cwd=R)
(R/'RETUNE_DONE.json').write_text(json.dumps({'batches':[1,64,128],'lrs':[.0005,.0042,.006]}))
