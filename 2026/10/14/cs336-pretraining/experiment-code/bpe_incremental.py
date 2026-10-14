"""Exact BPE with incremental pair counts; same tie-breaking as bpe.py."""
from collections import Counter,defaultdict
from pathlib import Path
import heapq,regex
from bpe import PATTERN
class Entry:
    __slots__=('count','pair')
    def __init__(self,count,pair):self.count=count;self.pair=pair
    def __lt__(self,other):return (self.count,self.pair)>(other.count,other.pair)
def train_bpe(input_path,vocab_size,special_tokens):
    text=Path(input_path).read_text(encoding='utf-8')
    chunks=regex.split('|'.join(map(regex.escape,special_tokens)),text) if special_tokens else [text]
    words=Counter()
    for chunk in chunks:words.update(regex.findall(PATTERN,chunk))
    del text,chunks
    seqs=[tuple(bytes([b]) for b in word.encode('utf-8')) for word in words]
    weights=list(words.values());del words
    freq=Counter();where=defaultdict(set)
    for i,seq in enumerate(seqs):
        for pair,n in Counter(zip(seq,seq[1:])).items():freq[pair]+=n*weights[i];where[pair].add(i)
    heap=[Entry(n,p) for p,n in freq.items()];heapq.heapify(heap)
    vocab={i:bytes([i]) for i in range(256)}
    vocab.update({256+i:t.encode('utf-8') for i,t in enumerate(special_tokens)})
    merges=[]
    while len(vocab)<vocab_size and heap:
        entry=heapq.heappop(heap);pair=entry.pair
        if freq.get(pair,0)!=entry.count or entry.count<=0:continue
        target=pair[0]+pair[1];vocab[len(vocab)]=target;merges.append(pair);changed=set()
        for i in list(where[pair]):
            old=seqs[i];old_counts=Counter(zip(old,old[1:]));new=[];j=0
            while j<len(old):
                if j+1<len(old) and (old[j],old[j+1])==pair:new.append(target);j+=2
                else:new.append(old[j]);j+=1
            seqs[i]=tuple(new);new_counts=Counter(zip(new,new[1:]))
            for p in old_counts.keys()|new_counts.keys():
                delta=new_counts[p]-old_counts[p]
                if delta:freq[p]+=delta*weights[i];changed.add(p)
                if p not in new_counts:where[p].discard(i)
                elif p not in old_counts:where[p].add(i)
        for p in changed:
            if freq[p]>0:heapq.heappush(heap,Entry(freq[p],p))
        if len(heap)>max(1000000,len(freq)*4):
            heap=[Entry(n,p) for p,n in freq.items() if n>0];heapq.heapify(heap)
        if len(merges)%1000==0:print('BPE merges',len(merges),flush=True)
    return vocab,merges
