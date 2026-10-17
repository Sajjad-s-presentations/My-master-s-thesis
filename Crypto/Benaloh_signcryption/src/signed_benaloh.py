"""Authenticated (Signed) Benaloh homomorphic encryption.

The design keeps the Benaloh ciphertext algebra unchanged and attaches an
Ed25519 signature to the canonical tuple (client_id, round_id, nonce,
ciphertext, weight). The server verifies the signature and authorization
before including the ciphertext in homomorphic aggregation.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import gcd, isqrt
from typing import Dict, Iterable, List, Sequence, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


SCALE = 10_000
SCHEME = "SBHE-Benaloh-Ed25519-v1"


def _is_probable_prime(n: int, rounds: int = 32) -> bool:
    if n < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False
    d, s = n - 1, 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _generate_prime(bits: int) -> int:
    if bits < 32:
        raise ValueError("prime size must be >= 32 bits")
    while True:
        x = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(x):
            return x


def _generate_prime_congruent_one(modulus: int, bits: int) -> int:
    if modulus <= 1:
        raise ValueError("modulus must be > 1")
    # q = k*r + 1. Choose k so q has the requested bit length.
    low = (1 << (bits - 1))
    high = (1 << bits) - 1
    k_min = max(1, (low - 1 + modulus - 1) // modulus)
    k_max = (high - 1) // modulus
    if k_min > k_max:
        raise ValueError("cannot construct a prime q with the requested size")
    while True:
        k = secrets.randbelow(k_max - k_min + 1) + k_min
        q = k * modulus + 1
        if q <= high and _is_probable_prime(q):
            return q


def _random_coprime(n: int) -> int:
    while True:
        x = secrets.randbelow(n - 2) + 2
        if gcd(x, n) == 1:
            return x


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def canonical_message(client_id: str, round_id: str, nonce: str, ciphertext: int, weight: int) -> bytes:
    """Canonical bytes signed by the client."""
    payload = {
        "scheme": SCHEME,
        "client_id": client_id,
        "round_id": round_id,
        "nonce": nonce,
        "ciphertext": str(ciphertext),
        "weight": int(weight),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def encode_value(value: float | str | Decimal) -> int:
    """Encode a value in [0,1] exactly to four decimal places."""
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("value must be a decimal number") from exc
    if not Decimal("0") <= x <= Decimal("1"):
        raise ValueError("value must be in [0, 1]")
    scaled = x * SCALE
    if scaled != scaled.to_integral_value():
        raise ValueError("value must have at most four decimal places")
    return int(scaled)


def decode_value(numerator: int, total_weight: int) -> Decimal:
    if total_weight <= 0:
        raise ValueError("total_weight must be positive")
    return (Decimal(numerator) / Decimal(SCALE)) / Decimal(total_weight)


@dataclass(frozen=True)
class BenalohPublicKey:
    n: int
    y: int
    r: int


class Benaloh:
    """Benaloh additive homomorphic encryption with BSGS decryption."""

    def __init__(self, bits: int = 256, r: int = 10_000_019):
        if bits < 128:
            raise ValueError("bits must be >= 128")
        if r <= 1:
            raise ValueError("r must be > 1")
        self.bits = bits
        self.r = r
        self.p = self.q = self.n = self.phi = self.y = self.u = None
        self.m = None
        self.baby = None
        self.factor = None

    @property
    def public_key(self) -> BenalohPublicKey:
        if self.n is None or self.y is None:
            raise ValueError("keygen must be called first")
        return BenalohPublicKey(self.n, self.y, self.r)

    def keygen(self) -> BenalohPublicKey:
        h = self.bits // 2
        while True:
            p = _generate_prime(h)
            if gcd(self.r, p - 1) == 1:
                break
        q = _generate_prime_congruent_one(self.r, h)
        n = p * q
        phi = (p - 1) * (q - 1)

        while True:
            y = _random_coprime(n)
            if pow(y, phi // self.r, n) != 1:
                break

        u = pow(y, phi // self.r, n)
        # BSGS table for the discrete logarithm in <u>, whose order is r.
        m = isqrt(self.r) + 1
        baby: Dict[int, int] = {}
        cur = 1
        for j in range(m):
            if cur not in baby:
                baby[cur] = j
            cur = cur * u % n
        factor = pow(pow(u, m, n), -1, n)

        self.p, self.q, self.n, self.phi, self.y, self.u = p, q, n, phi, y, u
        self.m, self.baby, self.factor = m, baby, factor
        return self.public_key

    def encrypt(self, m: int) -> int:
        if self.n is None:
            raise ValueError("keygen must be called first")
        if not isinstance(m, int) or not 0 <= m < self.r:
            raise ValueError(f"plaintext must be an integer in [0, {self.r - 1}]")
        randomness = _random_coprime(self.n)
        return pow(self.y, m, self.n) * pow(randomness, self.r, self.n) % self.n

    def decrypt(self, ciphertext: int) -> int:
        if self.n is None:
            raise ValueError("keygen must be called first")
        if not 0 < ciphertext < self.n or gcd(ciphertext, self.n) != 1:
            raise ValueError("invalid Benaloh ciphertext")
        target = pow(ciphertext, self.phi // self.r, self.n)
        gamma = target
        for i in range(self.m + 1):
            j = self.baby.get(gamma)
            if j is not None:
                x = i * self.m + j
                if x < self.r and pow(self.u, x, self.n) == target:
                    return x
            gamma = gamma * self.factor % self.n
        raise ValueError("Benaloh decryption failed: discrete logarithm not found")

    def aggregate(self, ciphertexts: Sequence[int], weights: Sequence[int]) -> int:
        if len(ciphertexts) != len(weights) or not ciphertexts:
            raise ValueError("ciphertexts and weights must be non-empty and have equal length")
        total = 0
        z = 1
        for c, w in zip(ciphertexts, weights):
            if not isinstance(w, int) or w <= 0:
                raise ValueError("weights must be positive integers")
            if not 0 < c < self.n or gcd(c, self.n) != 1:
                raise ValueError("invalid ciphertext in aggregation")
            total += w
            z = z * pow(c, w, self.n) % self.n
        if SCALE * total >= self.r:
            raise ValueError(
                "message-space overflow risk: SCALE * total_weight must be < r; "
                f"got {SCALE * total} >= {self.r}"
            )
        return z


@dataclass(frozen=True)
class SignedCiphertext:
    client_id: str
    round_id: str
    nonce: str
    ciphertext: int
    weight: int
    signature: str

    def to_dict(self) -> dict:
        return {
            "scheme": SCHEME,
            "client_id": self.client_id,
            "round_id": self.round_id,
            "nonce": self.nonce,
            "ciphertext": str(self.ciphertext),
            "weight": self.weight,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SignedCiphertext":
        if data.get("scheme") != SCHEME:
            raise ValueError("unsupported envelope scheme")
        return cls(
            client_id=str(data["client_id"]),
            round_id=str(data["round_id"]),
            nonce=str(data["nonce"]),
            ciphertext=int(data["ciphertext"]),
            weight=int(data["weight"]),
            signature=str(data["signature"]),
        )


class ClientSigner:
    """Client-side signing identity. Ed25519 is used only for authentication."""

    def __init__(self, client_id: str, private_key: Ed25519PrivateKey | None = None):
        if not client_id:
            raise ValueError("client_id is required")
        self.client_id = client_id
        self.private_key = private_key or Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    def export_private_key(self) -> str:
        raw = self.private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        return _b64e(raw)

    def export_public_key(self) -> str:
        raw = self.public_key.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return _b64e(raw)

    @classmethod
    def from_private_key(cls, client_id: str, encoded: str) -> "ClientSigner":
        raw = _b64d(encoded)
        return cls(client_id, Ed25519PrivateKey.from_private_bytes(raw))

    def sign_envelope(self, round_id: str, ciphertext: int, weight: int, nonce: str | None = None) -> SignedCiphertext:
        if not round_id:
            raise ValueError("round_id is required")
        if not isinstance(weight, int) or weight <= 0:
            raise ValueError("weight must be a positive integer")
        nonce = nonce or secrets.token_urlsafe(24)
        msg = canonical_message(self.client_id, round_id, nonce, ciphertext, weight)
        signature = self.private_key.sign(msg)
        return SignedCiphertext(
            client_id=self.client_id,
            round_id=round_id,
            nonce=nonce,
            ciphertext=ciphertext,
            weight=weight,
            signature=_b64e(signature),
        )


class SignedBenalohServer:
    """Server holding Benaloh secret material and an authorization registry."""

    def __init__(self, benaloh: Benaloh):
        self.benaloh = benaloh
        self.authorized_clients: Dict[str, Ed25519PublicKey] = {}
        self.used_nonces: set[Tuple[str, str, str]] = set()

    def register_client(self, client_id: str, public_key_b64: str) -> None:
        if not client_id:
            raise ValueError("client_id is required")
        self.authorized_clients[client_id] = Ed25519PublicKey.from_public_bytes(_b64d(public_key_b64))

    def verify(self, envelope: SignedCiphertext, expected_round: str) -> None:
        if envelope.round_id != expected_round:
            raise ValueError("rejected: stale or wrong round_id")
        if envelope.client_id not in self.authorized_clients:
            raise ValueError("rejected: unauthorized client")
        if envelope.weight <= 0:
            raise ValueError("rejected: invalid weight")
        key = (envelope.client_id, envelope.round_id, envelope.nonce)
        if key in self.used_nonces:
            raise ValueError("rejected: replayed nonce")
        try:
            self.authorized_clients[envelope.client_id].verify(
                _b64d(envelope.signature),
                canonical_message(
                    envelope.client_id,
                    envelope.round_id,
                    envelope.nonce,
                    envelope.ciphertext,
                    envelope.weight,
                ),
            )
        except (InvalidSignature, ValueError) as exc:
            raise ValueError("rejected: invalid signature or malformed signature") from exc
        if not 0 < envelope.ciphertext < self.benaloh.n:
            raise ValueError("rejected: ciphertext outside group")
        if gcd(envelope.ciphertext, self.benaloh.n) != 1:
            raise ValueError("rejected: ciphertext not in Z*_n")

    def accept_and_aggregate(self, envelopes: Iterable[SignedCiphertext], expected_round: str) -> tuple[int, int, int]:
        accepted: List[SignedCiphertext] = []
        seen_clients: set[str] = set()
        for envelope in envelopes:
            self.verify(envelope, expected_round)
            if envelope.client_id in seen_clients:
                raise ValueError(f"duplicate contribution from client {envelope.client_id}")
            seen_clients.add(envelope.client_id)
            accepted.append(envelope)

        if not accepted:
            raise ValueError("no valid client contributions")
        total_weight = sum(x.weight for x in accepted)
        if SCALE * total_weight >= self.benaloh.r:
            raise ValueError("weighted sum does not fit in the Benaloh plaintext space")
        aggregate = self.benaloh.aggregate(
            [x.ciphertext for x in accepted],
            [x.weight for x in accepted],
        )
        for x in accepted:
            self.used_nonces.add((x.client_id, x.round_id, x.nonce))
        return aggregate, total_weight, len(accepted)

    def decrypt_weighted_average(self, aggregate_ciphertext: int, total_weight: int) -> Decimal:
        numerator = self.benaloh.decrypt(aggregate_ciphertext)
        return decode_value(numerator, total_weight)


def create_client_submission(
    benaloh: Benaloh,
    signer: ClientSigner,
    value: float | str | Decimal,
    weight: int,
    round_id: str,
) -> SignedCiphertext:
    m = encode_value(value)
    ciphertext = benaloh.encrypt(m)
    return signer.sign_envelope(round_id, ciphertext, weight)


def fingerprint_public_key(public_key_b64: str) -> str:
    return hashlib.sha256(_b64d(public_key_b64)).hexdigest()
