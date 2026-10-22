from crypto.crypto_utils import (
    decrypt_bytes,
    encrypt_bytes,
    generate_rsa_keypair,
    new_aes_key,
    unwrap_key,
    wrap_key,
)


def test_aes_gcm_and_rsa_oaep_roundtrip():
    private_pem, public_pem = generate_rsa_keypair("demo-password")
    aes_key = new_aes_key()
    payload = encrypt_bytes(b"fake diploma", aes_key)
    assert decrypt_bytes(payload, aes_key) == b"fake diploma"
    assert unwrap_key(wrap_key(aes_key, public_pem), private_pem, "demo-password") == aes_key


def test_aes_gcm_nonce_is_unique():
    key = new_aes_key()
    first = encrypt_bytes(b"same", key)
    second = encrypt_bytes(b"same", key)
    assert first[:12] != second[:12]
    assert first != second
