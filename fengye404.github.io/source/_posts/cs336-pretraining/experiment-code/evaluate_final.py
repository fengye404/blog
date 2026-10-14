"""Evaluate the final checkpoint on non-overlapping validation windows, on Studio."""
from pathlib import Path
import json
import math
import time
import numpy as np
import torch
from model import TransformerLM
from training import cross_entropy

root = Path(__file__).resolve().parent
out = root / 'runs/baseline-40m'
model = TransformerLM(10000, 4, 512, 16, 1344, theta=10000,
                      max_seq_len=256, device='mps', dtype=torch.float32)
checkpoint = torch.load(out / 'step-5000.pt', map_location='cpu', weights_only=True)
model.load_state_dict(checkpoint['model'])
del checkpoint
model.eval()
data = np.memmap(root / 'data/valid.bin', dtype=np.uint16, mode='r')
windows = (len(data) - 1) // 256
loss_sum = 0.
started = time.perf_counter()
with torch.no_grad():
    for first in range(0, windows, 32):
        starts = np.arange(first, min(first + 32, windows)) * 256
        x = np.stack([data[i:i + 256] for i in starts]).astype(np.int64)
        y = np.stack([data[i + 1:i + 257] for i in starts]).astype(np.int64)
        loss = cross_entropy(model(torch.from_numpy(x).to('mps')),
                             torch.from_numpy(y).to('mps')).item()
        loss_sum += loss * len(starts)
result = dict(val_loss=loss_sum / windows, perplexity=math.exp(loss_sum / windows),
              windows=windows, evaluated_tokens=windows * 256,
              total_encoded_tokens=len(data), context_length=256,
              seconds=time.perf_counter() - started,
              method='non-overlapping 256-token windows; drop incomplete final window')
(out / 'evaluation.json').write_text(json.dumps(result, indent=2))
print(result)
