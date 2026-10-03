import base64
import hashlib
import hmac
import secrets
from typing import Tuple

from app.core.config import settings


def generate_aes128_key_and_iv() -> Tuple[bytes, bytes]:
    """Generates a cryptographically random 16-byte AES-128 key and 16-byte IV."""
    key = secrets.token_bytes(16)
    iv = secrets.token_bytes(16)
    return key, iv


def _derive_keys() -> Tuple[bytes, bytes]:
    """
    Derives separate encryption and authentication keys from the server master secret
    using SHA-256 HKDF-style key expansion.
    """
    master = settings.MASTER_ENCRYPTION_KEY.encode("utf-8")
    enc_key = hashlib.sha256(master + b"::ENC_KEY").digest()
    mac_key = hashlib.sha256(master + b"::MAC_KEY").digest()
    return enc_key, mac_key


def encrypt_key_cipher(raw_key: bytes, iv: bytes) -> str:
    """
    Encrypts the raw 16-byte key and 16-byte IV into an authenticated cipher string
    using CTR-mode keystream with HMAC-SHA256 authentication (Encrypt-then-MAC).
    Format: base64(nonce [16B] + mac_tag [32B] + ciphertext [32B])
    """
    enc_key, mac_key = _derive_keys()
    nonce = secrets.token_bytes(16)
    payload = raw_key + iv  # 32 bytes total

    # Generate 32-byte keystream
    keystream = hmac.new(enc_key, nonce + b"keystream", hashlib.sha256).digest()
    ciphertext = bytes(p ^ k for p, k in zip(payload, keystream))

    # Compute HMAC tag over nonce + ciphertext
    mac_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()

    package = nonce + mac_tag + ciphertext
    return base64.b64encode(package).decode("utf-8")


def decrypt_key_cipher(cipher_str: str) -> Tuple[bytes, bytes]:
    """
    Verifies authentication tag and decrypts the cipher string back into (raw_key, iv).
    Used by the key license server in Stage 3.
    """
    enc_key, mac_key = _derive_keys()
    raw = base64.b64decode(cipher_str.encode("utf-8"))

    if len(raw) != 80:  # 16 nonce + 32 tag + 32 ciphertext
        raise ValueError("Invalid cipher payload length")

    nonce = raw[:16]
    expected_tag = raw[16:48]
    ciphertext = raw[48:80]

    # Verify MAC in constant time
    actual_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, actual_tag):
        raise ValueError("Ciphertext authentication failed (tampering detected)")

    # Decrypt
    keystream = hmac.new(enc_key, nonce + b"keystream", hashlib.sha256).digest()
    decrypted = bytes(c ^ k for c, k in zip(ciphertext, keystream))

    raw_key = decrypted[:16]
    iv = decrypted[16:32]
    return raw_key, iv


def encrypt_credential_cipher(data: str) -> str:
    """
    Encrypts arbitrary-length string credentials (e.g. BYOS tokens/API keys)
    using authenticated CTR-keystream + HMAC-SHA256 (Encrypt-then-MAC).
    """
    enc_key, mac_key = _derive_keys()
    nonce = secrets.token_bytes(16)
    payload = data.encode("utf-8")

    # Generate sufficient keystream blocks
    blocks = (len(payload) + 31) // 32
    keystream = b"".join(
        hmac.new(enc_key, nonce + i.to_bytes(4, "big"), hashlib.sha256).digest()
        for i in range(blocks)
    )[: len(payload)]

    ciphertext = bytes(p ^ k for p, k in zip(payload, keystream))
    mac_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()

    package = nonce + mac_tag + ciphertext
    return base64.b64encode(package).decode("utf-8")


def decrypt_credential_cipher(cipher_str: str) -> str:
    """
    Verifies MAC and decrypts arbitrary-length credentials back into string.
    """
    enc_key, mac_key = _derive_keys()
    raw = base64.b64decode(cipher_str.encode("utf-8"))

    if len(raw) < 48:  # 16 nonce + 32 tag
        raise ValueError("Invalid credential cipher payload")

    nonce = raw[:16]
    expected_tag = raw[16:48]
    ciphertext = raw[48:]

    actual_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, actual_tag):
        raise ValueError("Credential authentication failed (tampering detected)")

    blocks = (len(ciphertext) + 31) // 32
    keystream = b"".join(
        hmac.new(enc_key, nonce + i.to_bytes(4, "big"), hashlib.sha256).digest()
        for i in range(blocks)
    )[: len(ciphertext)]

    decrypted = bytes(c ^ k for c, k in zip(ciphertext, keystream))
    return decrypted.decode("utf-8")

