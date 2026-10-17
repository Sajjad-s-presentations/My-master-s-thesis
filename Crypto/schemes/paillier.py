from common import generate_prime,lcm,random_coprime
class Paillier:
    SCALE=10000; operation='additive'; supports_average=True
    def __init__(self,bits=256,**kwargs): self.bits=max(128,bits)
    def keygen(self):
        h=self.bits//2; self.p=generate_prime(h); self.q=generate_prime(h)
        while self.q==self.p: self.q=generate_prime(h)
        self.n=self.p*self.q; self.n2=self.n*self.n; self.lam=lcm(self.p-1,self.q-1); self.mu=pow(self.lam,-1,self.n)
    def encrypt(self,m):
        if not 0<=m<self.n: raise ValueError('Paillier plaintext outside message space')
        r=random_coprime(self.n); return ((1+m*self.n)*pow(r,self.n,self.n2))%self.n2
    def decrypt(self,c):
        u=pow(c,self.lam,self.n2); return (((u-1)//self.n)*self.mu)%self.n
    def aggregate(self,cs,weights):
        z=1
        for c,w in zip(cs,weights): z=z*pow(c,int(w),self.n2)%self.n2
        return z
    def decode_average(self,m,total_weight): return m/(self.SCALE*total_weight)
