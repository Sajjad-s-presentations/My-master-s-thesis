# SBHE-Benaloh: Authenticated Homomorphic Weighted Aggregation

This project implements the proposed **Signed-Benaloh Homomorphic Encryption (SBHE)** construction for privacy-preserving weighted aggregation.

## Core idea

Each authorized client:

1. Converts a value in `[0,1]` to an integer with four decimal places.
2. Encrypts that integer with the server's Benaloh public key.
3. Signs a canonical transcript containing `client_id`, `round_id`, `nonce`, `ciphertext`, and `weight` with an Ed25519 private key.
4. Sends `(client_id, round_id, nonce, ciphertext, weight, signature)` to the server.

The server verifies authorization, signature, round freshness, nonce uniqueness, and ciphertext validity **before** aggregation. Only the Benaloh ciphertext is aggregated, so Benaloh's additive homomorphism remains unchanged:

`C_agg = product(C_i ** w_i) mod n`

After aggregation, the server decrypts the single aggregate ciphertext and divides by the scale and total weight to obtain the weighted average.

## Security boundary

The signature is an authentication/integrity layer around the Benaloh ciphertext; it is deliberately **not multiplied into the Benaloh ciphertext**. This avoids changing the algebraic structure that provides homomorphic addition.

The design assumes a trusted provisioning/registry step in which the server obtains the Ed25519 public key corresponding to every authorized client identity.

## Files

- `src/signed_benaloh.py`: complete implementation.
- `demo.py`: end-to-end demonstration, including tamper detection.
- `tests/test_signed_benaloh.py`: functional and security-oriented tests.
- `docs/thesis_chapter_fa.md`: Persian thesis-ready technical chapter.
- `requirements.txt`: dependencies.

## Run

```bash
python -m pip install -r requirements.txt
python demo.py
python -m unittest discover -s tests -v
```

For a production deployment, use a stronger key size and a parameter-selection procedure based on the maximum total weight. The default `r=10,000,019` is sufficient for total weight at most 1000 when values are restricted to `[0,1]` with four decimal places, because `10,000 * total_weight < r` must hold to prevent plaintext-space wraparound.
