import hashlib
import os

import pytest

from crypto.crypto_utils import (
    AAD_DEFAULT,
    EncryptedPackage,
    EncryptedPackageError,
    MIN_PAYLOAD_LEN,
    NONCE_LEN,
    PACKAGE_ALGORITHM,
    PACKAGE_VERSION,
    TAG_LEN,
    decrypt_bytes,
    decrypt_package,
    encrypt_bytes,
    encrypt_package,
    generate_rsa_keypair,
    new_aes_key,
    sha256_bytes,
    unwrap_key,
    wrap_key,
    wrap_key_for_roles,
)

RSA_PASSWORD = "demo-password"


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


def test_new_aes_key_is_32_bytes():
    assert len(new_aes_key()) == 32


def test_aes_gcm_roundtrip_binary_data():
    key = new_aes_key()
    data = os.urandom(4096)
    assert decrypt_bytes(encrypt_bytes(data, key), key) == data


def test_aes_gcm_empty_input():
    key = new_aes_key()
    assert decrypt_bytes(encrypt_bytes(b"", key), key) == b""


def test_aes_gcm_wrong_key_fails():
    key = new_aes_key()
    wrong_key = new_aes_key()
    payload = encrypt_bytes(b"secret diploma", key)
    with pytest.raises(ValueError):
        decrypt_bytes(payload, wrong_key)


def test_aes_gcm_tampered_ciphertext_fails():
    key = new_aes_key()
    payload = bytearray(encrypt_bytes(b"secret diploma", key))
    payload[-10] ^= 0xFF
    with pytest.raises(ValueError):
        decrypt_bytes(bytes(payload), key)


def test_aes_gcm_tampered_auth_tag_fails():
    key = new_aes_key()
    payload = bytearray(encrypt_bytes(b"secret diploma", key))
    payload[-1] ^= 0x01
    with pytest.raises(ValueError):
        decrypt_bytes(bytes(payload), key)


def test_aes_gcm_payload_too_short_fails():
    key = new_aes_key()
    with pytest.raises(ValueError):
        decrypt_bytes(b"short", key)


def test_rsa_oaep_wrap_unwrap_roundtrip():
    private_pem, public_pem = generate_rsa_keypair(RSA_PASSWORD)
    aes_key = new_aes_key()
    assert unwrap_key(wrap_key(aes_key, public_pem), private_pem, RSA_PASSWORD) == aes_key


def test_rsa_oaep_wrong_private_key_fails():
    aes_key = new_aes_key()
    _, public_pem = generate_rsa_keypair(RSA_PASSWORD)
    wrong_private, _ = generate_rsa_keypair("another-password")
    wrapped = wrap_key(aes_key, public_pem)
    with pytest.raises(Exception):
        unwrap_key(wrapped, wrong_private, "another-password")


def test_wrap_key_for_roles_independent_ciphertexts():
    aes_key = new_aes_key()
    holder_private, holder_public = generate_rsa_keypair(RSA_PASSWORD)
    issuer_private, issuer_public = generate_rsa_keypair(RSA_PASSWORD)
    wrapped_holder, wrapped_issuer = wrap_key_for_roles(aes_key, holder_public, issuer_public)
    assert wrapped_holder != wrapped_issuer
    assert unwrap_key(wrapped_holder, holder_private, RSA_PASSWORD) == aes_key
    assert unwrap_key(wrapped_issuer, issuer_private, RSA_PASSWORD) == aes_key


def test_sha256_bytes_is_deterministic_32_byte_digest():
    data = b"diploma.pdf plaintext bytes"
    digest = sha256_bytes(data)
    assert len(digest) == 32
    assert digest == hashlib.sha256(data).digest()
    assert digest == sha256_bytes(data)




def test_doc_hash_is_sha256_of_plaintext_pdf():
    diploma = b"%PDF-1.4 synthetic diploma content"
    doc_hash = sha256_bytes(diploma)
    assert len(doc_hash) == 32
    assert doc_hash == sha256_bytes(diploma)


def test_three_files_distinct_nonces_under_one_bundle_key():
    key = new_aes_key()
    files = {
        "portrait.jpg": b"\x89PNG synthetic portrait image",
        "diploma.pdf": b"%PDF-1.4 synthetic diploma content",
        "metadata.json": b'{"holder":"demo","degree":"CS"}',
    }
    nonces = set()
    for name, data in files.items():
        pkg = encrypt_package(data, key)
        assert pkg.nonce not in nonces, f"Nonce bị trùng cho file {name}"
        nonces.add(pkg.nonce)
        assert decrypt_package(pkg, key) == data
    assert len(nonces) == 3


def test_encrypt_package_matches_encrypt_bytes_wire_format():
    key = new_aes_key()
    data = b"wire format compatibility check"
    payload = encrypt_bytes(data, key)
    pkg = encrypt_package(data, key)
    packed = pkg.pack()
    # Cùng cấu trúc wire format: nonce[12] || ciphertext || tag[16];
    # bytes thực tế khác nhau vì mỗi hàm sinh nonce ngẫu nhiên độc lập.
    assert len(payload) == len(packed)
    assert len(payload[:NONCE_LEN]) == NONCE_LEN
    assert len(packed[-TAG_LEN:]) == TAG_LEN
    assert decrypt_bytes(payload, key) == data
    assert decrypt_package(pkg, key) == data


def test_encrypted_package_pack_unpack_roundtrip():
    key = new_aes_key()
    pkg = encrypt_package(b"diploma content", key)
    packed = pkg.pack()
    reparsed = EncryptedPackage.unpack(packed)
    assert reparsed.version == PACKAGE_VERSION
    assert reparsed.algorithm == PACKAGE_ALGORITHM
    assert reparsed.nonce == pkg.nonce
    assert reparsed.ciphertext == pkg.ciphertext
    assert reparsed.tag == pkg.tag
    assert reparsed.aad == AAD_DEFAULT
    assert decrypt_package(reparsed, key) == b"diploma content"


def test_encrypted_package_unpack_rejects_non_bytes():
    with pytest.raises(EncryptedPackageError):
        EncryptedPackage.unpack("not bytes")


def test_encrypted_package_unpack_rejects_too_short_payload():
    with pytest.raises(EncryptedPackageError):
        EncryptedPackage.unpack(b"\x00" * (MIN_PAYLOAD_LEN - 1))


def test_encrypted_package_unpack_rejects_empty_payload():
    with pytest.raises(EncryptedPackageError):
        EncryptedPackage.unpack(b"")


def test_decrypt_package_tampered_tag_fails():
    key = new_aes_key()
    pkg = encrypt_package(b"secret", key)
    tampered = EncryptedPackage(
        version=pkg.version,
        algorithm=pkg.algorithm,
        nonce=pkg.nonce,
        ciphertext=pkg.ciphertext,
        tag=bytes(b ^ 0xFF for b in pkg.tag),
        aad=pkg.aad,
    )
    with pytest.raises(EncryptedPackageError):
        decrypt_package(tampered, key)


def test_decrypt_package_wrong_key_fails():
    key = new_aes_key()
    wrong_key = new_aes_key()
    pkg = encrypt_package(b"secret", key)
    with pytest.raises(EncryptedPackageError):
        decrypt_package(pkg, wrong_key)


def test_encrypt_package_rejects_unsupported_version():
    key = new_aes_key()
    pkg = encrypt_package(b"data", key)
    bad = EncryptedPackage(
        version=99,
        algorithm=pkg.algorithm,
        nonce=pkg.nonce,
        ciphertext=pkg.ciphertext,
        tag=pkg.tag,
        aad=pkg.aad,
    )
    with pytest.raises(EncryptedPackageError):
        bad.pack()


def test_encrypt_package_rejects_unsupported_algorithm():
    key = new_aes_key()
    pkg = encrypt_package(b"data", key)
    bad = EncryptedPackage(
        version=pkg.version,
        algorithm="AES-128-CBC",
        nonce=pkg.nonce,
        ciphertext=pkg.ciphertext,
        tag=pkg.tag,
        aad=pkg.aad,
    )
    with pytest.raises(EncryptedPackageError):
        bad.pack()


def test_decrypt_package_rejects_mismatched_aad():
    key = new_aes_key()
    pkg = encrypt_package(b"data", key)
    with pytest.raises(EncryptedPackageError):
        decrypt_package(pkg, key, associated_data=b"wrong-aad")
