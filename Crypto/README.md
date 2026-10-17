# Homomorphic Encryption Benchmark - Stable Laptop Version

Python 3.10+, standard library only.

Algorithms:
- Paillier: additive homomorphism; directly computes weighted average.
- Damgard-Jurik: additive homomorphism, implemented in the stable s=1 specialization (mathematically Paillier-equivalent). The CLI exposes `--s 1` explicitly so the benchmark does not silently use an incorrect generalized decryption.
- Benaloh: additive homomorphism; message modulus r=10000019 (prime) covers all four-decimal encoded values 0..10000 and the default weighted sum (100 clients x weight <=10 = 10000).
- RSA: multiplicative homomorphism; independently tests 7*11 and reports weighted average as NOT_APPLICABLE.
- ElGamal: multiplicative homomorphism; independently tests 7*11 and reports weighted average as NOT_APPLICABLE.

Run all:
python main.py --scheme all --clients 100 --key-bits 512

Fast test:
python main.py --scheme all --clients 10 --key-bits 256

Single algorithms:
python main.py --scheme paillier
python main.py --scheme damgard_jurik --s 1
python main.py --scheme benaloh
python main.py --scheme rsa
python main.py --scheme elgamal

Simulation:
python simulator.py --scheme paillier --clients 5 --key-bits 256

Files:
results/benchmark.csv
results/simulation.log

Important: RSA and ElGamal are multiplicative, so they cannot directly implement the same additive weighted-average protocol. They are benchmarked correctly rather than being reported as failures.

This is an educational/research implementation, not production cryptography.
