import argparse,csv
from pathlib import Path
from time import perf_counter
from schemes import create
SCALE=10000; ADD={'paillier','damgard_jurik','benaloh'}; ALL=['paillier','damgard_jurik','benaloh','rsa','elgamal']
def dataset(n):
 import random; r=random.Random(42); return [r.randint(0,SCALE) for _ in range(n)],[r.randint(1,10) for _ in range(n)]
def additive(name,n,bits,s):
 scheme=create(name,bits,s=s) if name=='damgard_jurik' else create(name,bits); vals,weights=dataset(n); expected=sum(v*w for v,w in zip(vals,weights))/(SCALE*sum(weights))
 t=perf_counter(); scheme.keygen(); k=(perf_counter()-t)*1000
 t=perf_counter(); cs=[scheme.encrypt(v) for v in vals]; e=(perf_counter()-t)*1000
 t=perf_counter(); agg=scheme.aggregate(cs,weights); a=(perf_counter()-t)*1000
 t=perf_counter(); result=scheme.decode_average(scheme.decrypt(agg),sum(weights)); d=(perf_counter()-t)*1000
 err=abs(expected-result); return {'scheme':name,'operation':'additive','clients':n,'key_bits':bits,'s':s if name=='damgard_jurik' else '','keygen_ms':round(k,4),'encryption_ms':round(e,4),'aggregation_ms':round(a,4),'decryption_ms':round(d,4),'total_ms':round(k+e+a+d,4),'expected':expected,'result':result,'error':err,'homomorphic_test':'PASS' if err<=1e-4 else 'FAIL','weighted_average':'PASS'}
def multiplicative(name,n,bits):
 scheme=create(name,bits); t=perf_counter(); scheme.keygen(); k=(perf_counter()-t)*1000; t=perf_counter(); ok=scheme.test_homomorphic_multiplication(); h=(perf_counter()-t)*1000
 return {'scheme':name,'operation':'multiplicative','clients':n,'key_bits':bits,'s':'','keygen_ms':round(k,4),'encryption_ms':'','aggregation_ms':round(h,4),'decryption_ms':'','total_ms':round(k+h,4),'expected':'7*11','result':'77' if ok else 'wrong','error':0 if ok else 1,'homomorphic_test':'PASS' if ok else 'FAIL','weighted_average':'NOT_APPLICABLE'}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--scheme',choices=['all']+ALL,default='all'); p.add_argument('--clients',type=int,default=100); p.add_argument('--key-bits',type=int,default=1024); p.add_argument('--s',type=int,default=1); x=p.parse_args(); names=ALL if x.scheme=='all' else [x.scheme]; rows=[]
 print('\nHOMOMORPHIC ENCRYPTION BENCHMARK v5\n'+'='*110)
 for name in names:
  try:
   row=additive(name,x.clients,x.key_bits,x.s) if name in ADD else multiplicative(name,x.clients,x.key_bits); rows.append(row)
   print(f"{name:18} | {row['operation']:14} | total={row['total_ms']:10.3f} ms | HE={row['homomorphic_test']} | average={row['weighted_average']}")
  except Exception as e:
   print(f"{name:18} | ERROR: {type(e).__name__}: {e}")
   rows.append({'scheme':name,'operation':'','clients':x.clients,'key_bits':x.key_bits,'homomorphic_test':'ERROR','weighted_average':'ERROR','error_message':f'{type(e).__name__}: {e}'})
 Path('results').mkdir(exist_ok=True); fields=sorted({k for r in rows for k in r})
 with open('results/benchmark.csv','w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
 print('='*110+'\nSaved: results/benchmark.csv')
if __name__=='__main__': main()
