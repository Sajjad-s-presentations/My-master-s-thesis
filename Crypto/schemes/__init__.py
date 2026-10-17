from .paillier import Paillier
from .damgard_jurik import DamgardJurik
from .benaloh import Benaloh
from .rsa import RSA
from .elgamal import ElGamal

FACTORIES={'paillier':Paillier,'damgard_jurik':DamgardJurik,'benaloh':Benaloh,'rsa':RSA,'elgamal':ElGamal}
def create(name,bits=256,**kwargs): return FACTORIES[name](bits=bits,**kwargs)
