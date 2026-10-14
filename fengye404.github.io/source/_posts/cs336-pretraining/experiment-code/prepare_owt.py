"""Download the assignment OWT sample, train BPE on train only, encode both splits."""
from pathlib import Path
from functools import lru_cache
import gzip,hashlib,json,subprocess,time
import numpy as np
import regex
from bpe import PATTERN
from bpe_incremental import train_bpe
from tokenizer import Tokenizer
R=Path(__file__).resolve().parent;D=R/'owt';D.mkdir(exist_ok=True)
REV='488afadefc224407de5645a3c8c53b64ed923537';EOS='<|endoftext|>'
def docs(path):
    pending=''
    with gzip.open(path,'rt',encoding='utf-8') as f:
        while chunk:=f.read(1024*1024):
            pieces=(pending+chunk).split(EOS);pending=pieces.pop();yield from pieces
        if pending.strip():yield pending

def main():
    started=time.time()
    for split in ['train','valid']:
        p=D/f'{split}.txt.gz'
        if not p.exists():
            url=f'https://huggingface.co/datasets/stanford-cs336/owt-sample/resolve/{REV}/owt_{split}.txt.gz'
            subprocess.run(['curl','--proxy','http://127.0.0.1:7897','-fL','--retry','5','-C','-','-o',str(p)+'.part',url],check=True)
            Path(str(p)+'.part').replace(p)
    sample=D/'bpe-sample.txt'
    with sample.open('w') as f:
        for i,doc in enumerate(docs(D/'train.txt.gz')):
            if i==10000:break
            f.write(doc+EOS)
    print('BPE sample',sample.stat().st_size,flush=True)
    vocab,merges=train_bpe(str(sample),10000,[EOS]);assert len(vocab)==10000
    payload=dict(vocab={str(k):v.hex() for k,v in vocab.items()},merges=[[a.hex(),b.hex()] for a,b in merges],special_tokens=[EOS])
    (D/'tokenizer.json').write_text(json.dumps(payload))
    reverse={v:k for k,v in vocab.items()};ranks={pair:i for i,pair in enumerate(merges)}
    @lru_cache(maxsize=300000)
    def word(w):
        parts=[bytes([b]) for b in w.encode('utf-8')]
        while len(parts)>1:
            i=min(range(len(parts)-1),key=lambda i:ranks.get((parts[i],parts[i+1]),float('inf')))
            if (parts[i],parts[i+1]) not in ranks:break
            parts[i:i+2]=[parts[i]+parts[i+1]]
        return tuple(reverse[p] for p in parts)
    def encode(doc):return [t for w in regex.findall(PATTERN,doc) for t in word(w)]
    ref=Tokenizer(vocab,merges,[EOS])
    for i,doc in enumerate(docs(D/'valid.txt.gz')):
        if i==8:break
        assert encode(doc)==ref.encode(doc)
    stats={}
    for split in ['train','valid']:
        count=0;n=0
        with (D/f'{split}.bin').open('wb') as f:
            for doc in docs(D/f'{split}.txt.gz'):
                ids=encode(doc)+[reverse[EOS.encode()]];np.asarray(ids,dtype=np.uint16).tofile(f);count+=len(ids);n+=1
                if n%100000==0:print(split,n,count,flush=True)
        stats[split]=dict(documents=n,tokens=count)
    stats.update(revision=REV,vocab_size=10000,tokenizer_training_documents=10000,dtype='uint16',seconds=time.time()-started,tokenizer_sha256=hashlib.sha256((D/'tokenizer.json').read_bytes()).hexdigest())
    (D/'manifest.json').write_text(json.dumps(stats,indent=2));print(stats,flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        (D/'FAILED').write_text(str(e));raise
