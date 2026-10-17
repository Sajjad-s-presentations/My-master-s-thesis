from .paillier import Paillier
class DamgardJurik:
    SCALE=10000; operation='additive'; supports_average=True
    def __init__(self,bits=256,s=1,**kwargs):
        self.bits=max(128,bits); self.s=int(s)
        if self.s!=1: raise ValueError('Stable benchmark uses Damgard-Jurik s=1. Use --s 1.')
        self.core=Paillier(self.bits)
    def keygen(self): self.core.keygen(); self.n=self.core.n
    def encrypt(self,m): return self.core.encrypt(m)
    def decrypt(self,c): return self.core.decrypt(c)
    def aggregate(self,cs,weights): return self.core.aggregate(cs,weights)
    def decode_average(self,m,total_weight): return self.core.decode_average(m,total_weight)
