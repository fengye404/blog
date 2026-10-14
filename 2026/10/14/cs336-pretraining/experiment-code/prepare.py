from pathlib import Path
from functools import lru_cache
import hashlib, json, time
import numpy as np
import regex
from bpe import train_bpe, PATTERN
from tokenizer import Tokenizer
ROOT=Path(__file__).resolve().parent
EOS='<|endoftext|>'
def documents(path):
    pending=''
    with path.open(encoding='utf-8') as f:
        while chunk:=f.read(1024*1024):
            pending+=chunk
            parts=pending.split(EOS)
            pending=parts.pop()
            yield from parts
        if pending.strip(): yield pending

def main():
    started=time.time()
    # Explicitly bounded tokenizer training sample; LM sees the full train split.
    sample=ROOT/'data/bpe-train-10000docs.txt'
    with sample.open('w',encoding='utf-8') as f:
        for i,doc in enumerate(documents(ROOT/'data/train.txt')):
            if i>=10000:break
            f.write(doc+EOS)
    print('BPE training: first 10000 training documents',flush=True)
    vocab, merges=train_bpe(str(sample),10000,[EOS])
    assert len(vocab)==10000
    payload={'vocab':{str(k):v.hex() for k,v in vocab.items()},'merges':[[a.hex(),b.hex()] for a,b in merges],'special_tokens':[EOS]}
    (ROOT/'tokenizer.json').write_text(json.dumps(payload))
    print('BPE ready',time.time()-started,flush=True)
    reverse={v:k for k,v in vocab.items()}; ranks={pair:i for i,pair in enumerate(merges)}
    @lru_cache(maxsize=300000)
    def encode_word(word):
        parts=[bytes([b]) for b in word.encode('utf-8')]
        while len(parts)>1:
            i=min(range(len(parts)-1),key=lambda i:ranks.get((parts[i],parts[i+1]),float('inf')))
            if (parts[i],parts[i+1]) not in ranks:break
            parts[i:i+2]=[parts[i]+parts[i+1]]
        return tuple(reverse[x] for x in parts)
    def encode(doc):
        return [token for word in regex.findall(PATTERN,doc) for token in encode_word(word)]
    reference=Tokenizer(vocab,merges,[EOS])
    # Verify optimized pretoken cache/rank encoder against the original implementation.
    for i,doc in enumerate(documents(ROOT/'data/valid.txt')):
        if i>=8:break
        assert encode(doc)==reference.encode(doc),f'tokenizer mismatch {i}'
    stats={}
    for split, expected in [('train',2227753162),('valid',22502601)]:
        while (ROOT/f'data/{split}.txt').stat().st_size < expected:
            print('waiting for download',split,flush=True); time.sleep(10)
        assert (ROOT/f'data/{split}.txt').stat().st_size == expected
        count=0; docs=0
        with (ROOT/f'data/{split}.bin').open('wb') as out:
            for doc in documents(ROOT/f'data/{split}.txt'):
                ids=encode(doc)+[reverse[EOS.encode()]]
                np.asarray(ids,dtype=np.uint16).tofile(out)
                count+=len(ids);docs+=1
                if docs%100000==0: print(split,docs,count,flush=True)
        stats[split]={'documents':docs,'tokens':count}
    stats['tokenizer_training_documents']=10000
    stats['vocab_size']=len(vocab)
    stats['dtype']='uint16'
    stats['dataset']='roneneldan/TinyStories, TinyStoriesV2-GPT4'
    stats['dataset_revision']='f54c09fd23315a6f9c86f9dc80f725de7d8f9c64'
    stats['seconds']=time.time()-started
    stats['tokenizer_sha256']=hashlib.sha256((ROOT/'tokenizer.json').read_bytes()).hexdigest()
    (ROOT/'data/manifest.json').write_text(json.dumps(stats,indent=2))
    print(stats,flush=True)
if __name__=='__main__':main()
