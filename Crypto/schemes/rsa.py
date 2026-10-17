from common import generate_prime
from math import gcd
class RSA:
    operation='multiplicative'; supports_average=False
    def __init__(self,bits=256,**kwargs): self.bits=max(128,bits)
    def keygen(self):
        h=self.bits//2; self.p=generate_prime(h); self.q=generate_prime(h)
        while self.q==self.p: self.q=generate_prime(h)
        self.n=self.p*self.q; phi=(self.p-1)*(self.q-1); self.e=65537 if gcd(65537,phi)==1 else 3; self.d=pow(self.e,-1,phi)
    def encrypt(self,m): return pow(m%self.n,self.e,self.n)
    def decrypt(self,c): return pow(c,self.d,self.n)
    def test_homomorphic_multiplication(self):
        a,b=7,11; ca,cb=self.encrypt(a),self.encrypt(b); return self.decrypt(ca*cb%self.n)==a*b
