"""Plot recorded experiments only. Run after syncing experiments/ from Studio."""
from pathlib import Path
import json, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager
R=Path(__file__).resolve().parent
font=Path('/System/Library/Fonts/PingFang.ttc')
if not font.exists():font=next(Path('/System/Library/AssetsV2').glob('com_apple_MobileAsset_Font*/*.asset/AssetData/PingFang.ttc'),font)
if font.exists():
    fontManager.addfont(str(font));plt.rcParams['font.family']=FontProperties(fname=font).get_name()
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False})
def rows(name):
    p=R/'experiments'/name/'metrics.jsonl'
    if not p.exists():return []
    return [json.loads(x) for x in p.read_text().splitlines()]
def series(ax,name,label,key='val_loss',x='tokens'):
    data=[r for r in rows(name) if r.get(key) is not None and math.isfinite(r[key])]
    if not data:return
    div={'tokens':1e6,'seconds':60,'step':1}[x]
    ax.plot([r[x]/div for r in data],[r[key] for r in data],label=label,lw=1.8)
def finish(fig,axes,title,filename,x='tokens',ylabel='验证 loss（固定抽样）'):
    for ax in axes:
        ax.set(xlabel={'tokens':'累计训练 token（百万）','seconds':'累计耗时（分钟）','step':'训练步数'}[x],ylabel=ylabel)
        ax.grid(alpha=.18);ax.legend(frameon=False,fontsize=9)
    fig.suptitle(title,fontsize=15);fig.savefig(R/filename,dpi=180,facecolor='white');plt.close(fig)
def dual(names,title,filename):
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for ax,x in zip(axes,['tokens','seconds']):
        for name,label in names:series(ax,name,label,x=x)
        ax.set(xlabel='累计训练 token（百万）' if x=='tokens' else '累计耗时（分钟）',ylabel='验证 loss（固定抽样）');ax.grid(alpha=.18);ax.legend(frameon=False,fontsize=9)
    fig.suptitle(title,fontsize=15);fig.savefig(R/filename,dpi=180,facecolor='white');plt.close(fig)
if __name__=='__main__':
    dual([(f'lr-pilot-{lr:g}',f'LR = {lr:g}') for lr in [.0003,.001,.003,.01]],'学习率筛选 · 每组 819.2 万 token','lr-pilots.png')
    names=[(p.parent.name,p.parent.name.removeprefix('lr-stability-')) for p in sorted((R/'experiments').glob('lr-stability-*/result.json'))]
    if names:
        fig,axes=plt.subplots(1,1,figsize=(7,4.5),layout='constrained')
        for name,label in names:series(axes,name,'LR = '+label,key='train_loss',x='step')
        axes.set_yscale('log');finish(fig,[axes],'大学习率的训练过程','lr-stability.png',x='step',ylabel='训练 loss（对数坐标）')
    selection=R/'selection.json'
    if selection.exists():
        sel=json.loads(selection.read_text());ref=sel['reference']
        dual(list({name:(name,f'LR = {lr:g}') for _,lr,name in sel['full']}.values()),'学习率复验 · 每组 4096 万 token','lr-full.png')
        dual([(ref,'Pre-norm 基线'),('ablation-no_norm','移除 RMSNorm'),('ablation-no_norm-lower','移除 RMSNorm，LR / 10'),('ablation-post_norm','Post-norm')],'RMSNorm 消融 · 相同模型与训练预算','norm-ablation.png')
        failed_norm=R/'experiments/ablation-no_norm/result.json'
        if failed_norm.exists() and json.loads(failed_norm.read_text())['status']=='diverged':
            fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
            for name,label in [(ref,'Pre-norm 基线'),('ablation-no_norm','移除 RMSNorm'),('ablation-no_norm-lower','移除 RMSNorm，LR / 10')]:
                series(ax,name,label,key='train_loss',x='step')
            ax.set_yscale('log');ax.set_xlim(0,300);finish(fig,[ax],'移除 RMSNorm · 前 300 步训练 loss','norm-stability.png',x='step',ylabel='训练 loss（对数坐标）')
        dual([(ref,'RoPE + SwiGLU'),('ablation-nope','NoPE + SwiGLU'),('ablation-silu','RoPE + SiLU')],'位置编码与前馈网络消融','architecture-ablation.png')
        dual([('custom-untied_small_init','独立权重，同值初始化'),('custom-tied','共享权重，同值初始化')],'Embedding 与 LM head 权重共享','weight-tying.png')
    batches=[(p.parent.name,'Batch = '+p.parent.name.removeprefix('batch-')) for p in sorted((R/'experiments').glob('batch-*/result.json')) if 'probe' not in p.parent.name and 'retuned' not in p.parent.name]
    if batches:dual(batches,'Batch 对比 · 每组约 409.6 万 token','batch-comparison.png')
    if all((R/'experiments'/f'batch-{b}-retuned/result.json').exists() for b in [1,64,128]):
        fig,axes=plt.subplots(1,3,figsize=(13,4.2),layout='constrained')
        for ax,b,lr in zip(axes,[1,64,128],[.0005,.0042,.006]):
            series(ax,f'batch-{b}','LR = 0.003')
            series(ax,f'batch-{b}-retuned',f'LR = {lr:g}')
            ax.set_title(f'Batch = {b}')
        finish(fig,axes,'不同 batch 的学习率复验','batch-lr-retune.png')
    if rows('owt-baseline'):
        fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
        for ax,x in zip(axes,['tokens','seconds']):
            series(ax,'owt-baseline','训练 loss',key='train_loss',x=x);series(ax,'owt-baseline','验证 loss',x=x)
            ax.set(xlabel='累计训练 token（百万）' if x=='tokens' else '累计耗时（分钟）',ylabel='Cross-entropy loss');ax.grid(alpha=.18);ax.legend(frameon=False)
        fig.suptitle('OpenWebText · 22.70M 参数 · 4096 万训练 token',fontsize=15);fig.savefig(R/'owt-loss.png',dpi=180,facecolor='white');plt.close(fig)
