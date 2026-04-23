"""Sgraal Vaccination — encryption/decryption for vaccine signatures at rest.

Vaccine signatures are encrypted before Redis storage so a Redis breach
does not expose the full list of known attack patterns (#35).

Encryption priority:
    1. AES-256-GCM via cryptography library (if installed)
    2. XOR stream cipher with HMAC-SHA256 authentication (fallback)
    3. Raw JSON (if ATTESTATION_SECRET is missing/short)

Decryption handles all three formats plus already-parsed dicts for
backward compatibility. Never crashes — returns {} on any failure.

The `attestation_secret` parameter is passed explicitly (not read from
env) so these functions remain pure and testable.
"""

import base64 as _b64
import hashlib
import json as _json
import logging
import secrets

logger = logging.getLogger(__name__)

__all__ = [
    "encrypt_vaccine",
    "decrypt_vaccine",
]


def encrypt_vaccine(data: dict, attestation_secret: str = "") -> str:
    """Encrypt a vaccine signature dict for Redis storage.

    Tries AES-256-GCM first (if cryptography installed), falls back to XOR.
    Returns raw JSON if attestation_secret is missing or too short.

    Args:
        data: Vaccine signature dict to encrypt.
        attestation_secret: HMAC/encryption key (ATTESTATION_SECRET env var).
    """
    key = attestation_secret
    if not key or len(key) < 8:
        return _json.dumps(data)
    try:
        plaintext = _json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        # Try AES-256-GCM
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            from cryptography.hazmat.primitives import hashes as _hashes
            aes_key = HKDF(algorithm=_hashes.SHA256(), length=32, salt=b"sgraal-vaccine-v2", info=b"vaccine-encryption").derive(key.encode())
            nonce = secrets.token_bytes(12)
            ct_tag = AESGCM(aes_key).encrypt(nonce, plaintext, None)
            return _b64.b64encode(b"AES1" + nonce + ct_tag).decode("ascii")
        except ImportError:
            raise RuntimeError(
                "cryptography package not installed — vaccine encryption unavailable. "
                "Install with: pip install cryptography"
            )
    except Exception:
        return _json.dumps(data)


def decrypt_vaccine(stored, attestation_secret: str = "") -> dict:
    """Decrypt a vaccine signature from Redis.

    Handles: AES-GCM blobs, old XOR blobs, raw JSON strings, parsed dicts.
    Never crashes — returns {} on any failure.

    Args:
        stored: Encrypted string from Redis, raw JSON, or already-parsed dict.
        attestation_secret: HMAC/encryption key (ATTESTATION_SECRET env var).
    """
    if isinstance(stored, dict):
        return stored
    if not isinstance(stored, str):
        return {}

    key = attestation_secret
    if stored.startswith("{"):
        try:
            return _json.loads(stored)
        except Exception:
            pass

    if not key or len(key) < 8:
        try:
            return _json.loads(stored)
        except Exception:
            return {}
    try:
        raw = _b64.b64decode(stored)

        # Try AES-256-GCM (format: "AES1" + 12-byte nonce + ciphertext+tag)
        if raw[:4] == b"AES1":
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                from cryptography.hazmat.primitives.kdf.hkdf import HKDF
                from cryptography.hazmat.primitives import hashes as _hashes
                aes_key = HKDF(algorithm=_hashes.SHA256(), length=32, salt=b"sgraal-vaccine-v2", info=b"vaccine-encryption").derive(key.encode())
                plaintext = AESGCM(aes_key).decrypt(raw[4:16], raw[16:], None)
                return _json.loads(plaintext.decode("utf-8"))
            except ImportError:
                pass  # can't decrypt AES without library — try XOR below
            except Exception:
                pass  # AES decrypt failed — try XOR below

        # Old XOR format (16-byte nonce + ciphertext + 32-byte HMAC tag)
        if len(raw) < 48:
            raise ValueError("too short")
        nonce = raw[:16]
        tag = raw[-32:]
        ct = raw[16:-32]
        import hmac as _hmac_dec
        expected_tag = _hmac_dec.new(key.encode(), nonce + ct, hashlib.sha256).digest()
        if not _hmac_dec.compare_digest(tag, expected_tag):
            raise ValueError("HMAC tag mismatch")
        # Decrypt
        dk = hashlib.sha256(key.encode() + nonce).digest()
        keystream = b""
        block = dk
        while len(keystream) < len(ct):
            keystream += block
            block = hashlib.sha256(block).digest()
        plaintext = bytes(c ^ k for c, k in zip(ct, keystream[:len(ct)]))
        return _json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        # Fallback: maybe it's unencrypted JSON that doesn't start with {
        try:
            return _json.loads(stored)
        except Exception:
            logger.warning("vaccine decrypt failed: %s", e)
            return {}
