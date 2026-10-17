from common import generate_prime,random_coprime,is_probable_prime
class ElGamal:
    operation='multiplicative'; supports_average=False
    def __init__(self,bits=256,**kwargs): self.bits=max(128,bits)
    def keygen(self):
        # Safe-prime group; for benchmark sizes this is practical and deterministic in behavior.
        while True:
            q=generate_prime(self.bits-1); p=2*q+1
            if is_probable_prime(p): break
        self.p=p; self.q=q; self.g=2; self.x=1+random_coprime(q-2); self.y=pow(self.g,self.x,p)
    def encrypt(self,m):
        k=1+random_coprime(self.q-2); a=pow(self.g,k,self.p); b=m%self.p*pow(self.y,k,self.p)%self.p; return a,b
    def decrypt(self,c):
        a,b=c; return b*pow(pow(a,self.x,self.p),-1,self.p)%self.p
    def test_homomorphic_multiplication(self):
        a,b=7,11; ca,cb=self.encrypt(a),self.encrypt(b); c=((ca[0]*cb[0])%self.p,(ca[1]*cb[1])%self.p); return self.decrypt(c)==a*b
