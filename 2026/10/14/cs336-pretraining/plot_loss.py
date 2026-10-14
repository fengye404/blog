"""Render the measured training log; run beside metrics.jsonl."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager

root = Path(__file__).resolve().parent
rows = [json.loads(line) for line in (root / 'metrics.jsonl').read_text().splitlines()]
font = Path('/System/Library/Fonts/PingFang.ttc')
if not font.exists():
    font = next(Path('/System/Library/AssetsV2').glob('com_apple_MobileAsset_Font*/*.asset/AssetData/PingFang.ttc'), font)
if font.exists():
    fontManager.addfont(str(font))
    plt.rcParams['font.family'] = FontProperties(fname=font).get_name()
plt.rcParams.update({'font.size': 12, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.unicode_minus': False})
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
for ax, x, label in zip(axes,
                       [[r['step'] for r in rows], [r['seconds'] / 60 for r in rows]],
                       ['训练步数', '累计耗时（分钟）']):
    ax.plot(x, [r['train_loss'] for r in rows], color='#96a5b8', lw=1.3,
            alpha=.85, label='训练 loss（当前 batch）')
    ax.plot(x, [r['val_loss'] for r in rows], color='#2263ac', lw=2.2,
            label='验证 loss（固定抽样）')
    ax.set(xlabel=label, ylabel='Cross-entropy loss')
    ax.grid(alpha=.15)
    ax.legend(frameon=False, fontsize=10)
fig.suptitle('TinyStories · 22.70M 参数 · 4096 万训练 token', fontsize=15)
fig.savefig(root / 'training-loss.png', dpi=180, facecolor='white')
plt.close(fig)
