import argparse
from pathlib import Path
from time import perf_counter
from schemes import create
SCALE=10000
class Logger:
 def __init__(self): Path('results').mkdir(exist_ok=True); Path('results/simulation.log').write_text('',encoding='utf-8'); self.i=1
 def log(self,actor,action,detail=''):
  s=f'[{self.i:03d}] {actor:<12} {action:<34} {detail}'; print(s); open('results/simulation.log','a',encoding='utf-8').write(s+'\n'); self.i+=1
def run(name,n,bits,s):
 L=Logger(); scheme=create(name,bits,s=s) if name=='damgard_jurik' else create(name,bits); import random; r=random.Random(42); vals=[r.randint(0,SCALE) for _ in range(n)]; weights=[r.randint(1,10) for _ in range(n)]
 L.log('SYSTEM','Start simulation',f'{name}, clients={n}, bits={bits}')
 t=perf_counter(); scheme.keygen(); L.log('SERVER','Generate key pair',f'{(perf_counter()-t)*1000:.3f} ms'); L.log('SERVER','Publish public key','clients receive public parameters')
 cs=[]
 for i,(v,w) in enumerate(zip(vals,weights),1):
  L.log(f'CLIENT-{i:03}','Create plaintext',f'encoded={v}, weight={w}'); t=perf_counter(); c=scheme.encrypt(v); L.log(f'CLIENT-{i:03}','Encrypt plaintext',f'{(perf_counter()-t)*1000:.3f} ms'); cs.append(c); L.log('SERVER','Receive ciphertext',f'client={i}; plaintext hidden')
 if name in {'paillier','damgard_jurik','benaloh'}:
  t=perf_counter(); agg=scheme.aggregate(cs,weights); L.log('SERVER','Homomorphic aggregation',f'{(perf_counter()-t)*1000:.3f} ms'); dec=scheme.decrypt(agg); L.log('SERVER','Decrypt final aggregate',f'encoded_sum={dec}'); result=scheme.decode_average(dec,sum(weights)); expected=sum(v*w for v,w in zip(vals,weights))/(SCALE*sum(weights)); L.log('SERVER','Weighted average',f'{result:.8f}'); L.log('VERIFY','Correctness',f'expected={expected:.8f}; error={abs(expected-result):.10f}')
 else:
  a,b=7,11; ca,cb=scheme.encrypt(a),scheme.encrypt(b); combined=scheme.decrypt((ca*cb)%scheme.n) if name=='rsa' else scheme.decrypt(((ca[0]*cb[0])%scheme.p,(ca[1]*cb[1])%scheme.p)); L.log('SERVER','Homomorphic multiplication','7 * 11'); L.log('VERIFY','Correctness',f'expected=77; result={combined}')
 L.log('SYSTEM','Simulation finished','results/simulation.log')
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--scheme',choices=['paillier','damgard_jurik','benaloh','rsa','elgamal'],default='paillier'); p.add_argument('--clients',type=int,default=5); p.add_argument('--key-bits',type=int,default=256); p.add_argument('--s',type=int,default=1); a=p.parse_args(); run(a.scheme,a.clients,a.key_bits,a.s)
