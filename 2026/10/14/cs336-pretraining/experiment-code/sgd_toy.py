"""Course SGD toy example; execute on Studio."""
from pathlib import Path
import json,math,torch
results=[]
for lr in [1,10,100,1000]:
    torch.manual_seed(42);w=torch.nn.Parameter(5*torch.randn(10,10))
    initial=w.square().mean().item();losses=[initial]
    for t in range(10):
        w.grad=None;loss=w.square().mean();loss.backward()
        with torch.no_grad():w.add_(w.grad,alpha=-lr/math.sqrt(t+1))
        losses.append(w.square().mean().item())
    results.append(dict(lr=lr,losses=losses,ratio_after_10=losses[-1]/initial))
Path(__file__).with_name('sgd-toy.json').write_text(json.dumps(results,indent=2));print(results)
