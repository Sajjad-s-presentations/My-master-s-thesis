from common import generate_prime,generate_prime_congruent_one,random_coprime
from math import gcd
class Benaloh:
    SCALE=10000; operation='additive'; supports_average=True
    def __init__(self,bits=256,r=10000019,**kwargs): self.bits=max(128,bits); self.r=r
    def keygen(self):
        h=self.bits//2
        while True:
            self.p=generate_prime(h)
            if gcd(self.r,self.p-1)==1: break
        self.q=generate_prime_congruent_one(self.r,h)
        self.n=self.p*self.q; self.phi=(self.p-1)*(self.q-1)
        while True:
            self.y=random_coprime(self.n)
            if pow(self.y,self.phi//self.r,self.n)!=1: break
        # u = y^(phi/r) has order r.
        self.u=pow(self.y,self.phi//self.r,self.n)
        # Baby-step/giant-step discrete log. O(sqrt(r)) memory/time,
        # unlike the previous version which attempted to store all r entries.
        import math
        self.m=math.isqrt(self.r)+1
        self.baby={}
        cur=1
        for j in range(self.m):
            if cur not in self.baby: self.baby[cur]=j
            cur=cur*self.u%self.n
        factor=pow(pow(self.u,self.m,self.n),-1,self.n)
        self.factor=factor

    def encrypt(self,m):
        if not 0<=m<self.r: raise ValueError(f'Benaloh plaintext must be 0..{self.r-1}')
        u=random_coprime(self.n); return pow(self.y,m,self.n)*pow(u,self.r,self.n)%self.n
    def decrypt(self,c):
        target=pow(c,self.phi//self.r,self.n)
        gamma=target
        for i in range(self.m+1):
            j=self.baby.get(gamma)
            if j is not None:
                x=i*self.m+j
                if x < self.r and pow(self.u,x,self.n)==target:
                    return x
            gamma=gamma*self.factor%self.n
        raise ValueError('Benaloh decryption failed: discrete logarithm not found')
    def aggregate(self,cs,weights):
        z=1
        for c,w in zip(cs,weights): z=z*pow(c,int(w),self.n)%self.n
        return z
    def decode_average(self,m,total_weight): return m/(self.SCALE*total_weight)
