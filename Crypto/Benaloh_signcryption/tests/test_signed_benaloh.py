import unittest
from dataclasses import replace
from decimal import Decimal

from src.signed_benaloh import (
    Benaloh,
    ClientSigner,
    SignedBenalohServer,
    create_client_submission,
)


class SignedBenalohTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Benaloh(bits=128, r=10000019)
        cls.b.keygen()

    def test_encrypt_decrypt(self):
        for m in (0, 1, 42, 9999, 10000):
            self.assertEqual(self.b.decrypt(self.b.encrypt(m)), m)

    def test_homomorphic_weighted_sum(self):
        values = [7000, 8500, 9000]
        weights = [1, 2, 1]
        cs = [self.b.encrypt(x) for x in values]
        agg = self.b.aggregate(cs, weights)
        self.assertEqual(self.b.decrypt(agg), sum(v*w for v, w in zip(values, weights)))

    def test_end_to_end_signed_average(self):
        server = SignedBenalohServer(self.b)
        clients = [ClientSigner(f"c{i}") for i in range(3)]
        for c in clients:
            server.register_client(c.client_id, c.export_public_key())
        round_id = "r1"
        envelopes = [
            create_client_submission(self.b, clients[0], "0.7000", 1, round_id),
            create_client_submission(self.b, clients[1], "0.8500", 2, round_id),
            create_client_submission(self.b, clients[2], "0.9000", 1, round_id),
        ]
        agg, total_weight, count = server.accept_and_aggregate(envelopes, round_id)
        self.assertEqual(count, 3)
        self.assertEqual(total_weight, 4)
        self.assertEqual(server.decrypt_weighted_average(agg, total_weight), Decimal("0.825"))

    def test_unauthorized_client_is_rejected(self):
        server = SignedBenalohServer(self.b)
        c = ClientSigner("intruder")
        envelope = create_client_submission(self.b, c, "0.5000", 1, "r1")
        with self.assertRaises(ValueError):
            server.verify(envelope, "r1")

    def test_tampered_weight_is_rejected(self):
        server = SignedBenalohServer(self.b)
        c = ClientSigner("c1")
        server.register_client(c.client_id, c.export_public_key())
        e = create_client_submission(self.b, c, "0.5000", 1, "r1")
        with self.assertRaises(ValueError):
            server.verify(replace(e, weight=99), "r1")

    def test_tampered_ciphertext_is_rejected(self):
        server = SignedBenalohServer(self.b)
        c = ClientSigner("c1")
        server.register_client(c.client_id, c.export_public_key())
        e = create_client_submission(self.b, c, "0.5000", 1, "r1")
        with self.assertRaises(ValueError):
            server.verify(replace(e, ciphertext=(e.ciphertext + 1) % self.b.n), "r1")

    def test_replay_is_rejected_after_acceptance(self):
        server = SignedBenalohServer(self.b)
        c = ClientSigner("c1")
        server.register_client(c.client_id, c.export_public_key())
        e = create_client_submission(self.b, c, "0.5000", 1, "r1")
        server.accept_and_aggregate([e], "r1")
        with self.assertRaises(ValueError):
            server.verify(e, "r1")

    def test_wrong_round_is_rejected(self):
        server = SignedBenalohServer(self.b)
        c = ClientSigner("c1")
        server.register_client(c.client_id, c.export_public_key())
        e = create_client_submission(self.b, c, "0.5000", 1, "r1")
        with self.assertRaises(ValueError):
            server.verify(e, "r2")

    def test_precision_is_enforced(self):
        c = ClientSigner("c1")
        with self.assertRaises(ValueError):
            create_client_submission(self.b, c, "0.12345", 1, "r1")


if __name__ == "__main__":
    unittest.main()
