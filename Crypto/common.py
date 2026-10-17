from math import gcd
from secrets import randbits, randbelow

def is_probable_prime(n, rounds=8):
    if n < 2: return False
    for p in (2,3,5,7,11,13,17,19,23,29,31,37):
        if n == p: return True
        if n % p == 0: return False
    d=n-1; s=0
    while d%2==0: d//=2; s+=1
    for _ in range(rounds):
        a=2+randbelow(n-3); x=pow(a,d,n)
        if x in (1,n-1): continue
        for _ in range(s-1):
            x=pow(x,2,n)
            if x==n-1: break
        else: return False
    return True

def generate_prime(bits):
    bits=max(32,int(bits))
    while True:
        n=randbits(bits)|(1<<(bits-1))|1
        if is_probable_prime(n): return n

def generate_prime_congruent_one(modulus,bits):
    # Generate q = k*modulus + 1 directly; avoids rejection sampling q % modulus == 1.
    bits=max(32,int(bits)); low=1<<(bits-1); high=1<<bits
    k0=(low-1)//modulus+1
    while True:
        k=k0+randbelow(max(1,(high//modulus)-k0))
        q=k*modulus+1
        if q<high and is_probable_prime(q): return q

def lcm(a,b): return a//gcd(a,b)*b

def random_coprime(n):
    while True:
        x=2+randbelow(max(2,n-2))
        if gcd(x,n)==1: return x
