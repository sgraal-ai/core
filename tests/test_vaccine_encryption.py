"""Tests for #35: vaccine encryption at rest in Redis.

Vaccine signatures are now encrypted via _encrypt_vaccine/_decrypt_vaccine
before storage. A Redis breach no longer exposes the known attack signature
list in plaintext.
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import _encrypt_vaccine, _decrypt_vaccine


class TestVaccineEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting and decrypting a vaccine dict must produce the original."""
        original = {
            "signature_id": "vax_test_001",
            "content_hash_prefix": "abcd1234abcd1234",
            "domain": "fintech",
            "attack_type": "consensus_poisoning",
            "downstream_pattern": "high",
            "detected_at": "2026-04-17T10:00:00Z",
        }
        encrypted = _encrypt_vaccine(original)
        # Encrypted form should NOT be readable JSON (unless ATTESTATION_SECRET is empty)
        if os.getenv("ATTESTATION_SECRET", ""):
            assert not encrypted.startswith("{"), (
                "Encrypted vaccine looks like plaintext JSON — encryption may not have fired"
            )
        decrypted = _decrypt_vaccine(encrypted)
        assert decrypted == original, (
            f"Roundtrip failed: original={original}, decrypted={decrypted}"
        )

    def test_backward_compat_with_unencrypted_data(self):
        """Old unencrypted vaccines (raw JSON strings or already-parsed dicts)
        must still be readable after the encryption change."""
        # Case 1: raw JSON string (as stored before encryption was added)
        raw_json = '{"signature_id":"old_vax","domain":"medical","attack_type":"timestamp_forgery"}'
        result = _decrypt_vaccine(raw_json)
        assert result["signature_id"] == "old_vax"
        assert result["domain"] == "medical"

        # Case 2: already-parsed dict (redis_get may auto-deserialize)
        already_dict = {"signature_id": "dict_vax", "domain": "legal"}
        result2 = _decrypt_vaccine(already_dict)
        assert result2["signature_id"] == "dict_vax"

        # Case 3: empty/None
        assert _decrypt_vaccine("") == {}
        assert _decrypt_vaccine({}) == {}
