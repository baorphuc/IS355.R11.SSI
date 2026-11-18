"""M2 security/fixture checks. Crypto core unchanged; no real Kubo in this file."""
import importlib.util
import json
import secrets
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization

from crypto.crypto_utils import (
    EncryptedPackage, EncryptedPackageError, decrypt_bytes, decrypt_package,
    encrypt_bytes, encrypt_package, generate_rsa_keypair, new_aes_key,
    sha256_bytes, unwrap_key, wrap_key, wrap_key_for_roles,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/crypto_ipfs_v1"
spec = importlib.util.spec_from_file_location("crypto_ipfs_m2", ROOT / "tests/manual/crypto_ipfs_m2.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture(scope="module")
def role_keys():
    passwords = [secrets.token_urlsafe(24) for _ in range(3)]
    return [(generate_rsa_keypair(password), password) for password in passwords]


@pytest.mark.parametrize("name", runner.NAMES)
def test_m2_valid_fixture_roundtrip_and_reopen(name):
    source = (FIXTURES / name).read_bytes()
    inventory = json.loads((FIXTURES / "inventory.json").read_text())
    assert runner.digest(source) == inventory[name]["sha256"]
    key = new_aes_key()
    restored = decrypt_bytes(encrypt_bytes(source, key), key)
    assert restored == source
    runner.validate_file(name, restored)


@pytest.mark.parametrize("offset", [0, 12, -1], ids=["nonce", "ciphertext", "tag"])
def test_m2_tamper_rejected(offset):
    key = new_aes_key()
    payload = bytearray(encrypt_bytes(b"synthetic document", key))
    payload[offset] ^= 1
    with pytest.raises(EncryptedPackageError):
        decrypt_bytes(bytes(payload), key)


def test_m2_wrong_aes_key_rejected():
    with pytest.raises(EncryptedPackageError):
        decrypt_bytes(encrypt_bytes(b"synthetic", new_aes_key()), new_aes_key())


def test_m2_aad_mismatch_rejected():
    key = new_aes_key()
    with pytest.raises(EncryptedPackageError):
        decrypt_package(encrypt_package(b"synthetic", key), key, b"wrong-aad")


def test_m2_changed_aad_even_when_field_and_argument_match_rejected():
    key = new_aes_key()
    package = replace(encrypt_package(b"synthetic", key), aad=b"wrong-aad")
    with pytest.raises(EncryptedPackageError):
        decrypt_package(package, key, b"wrong-aad")


def test_m2_nonce_uniqueness_1000_same_key_plaintext():
    key = new_aes_key()
    nonces = {encrypt_bytes(b"same synthetic plaintext", key)[:12] for _ in range(1000)}
    assert len(nonces) == 1000  # sample observation, not a proof of global uniqueness


def test_m2_both_roles_unwrap_and_cross_role_rejected(role_keys):
    ((holder_private, holder_public), holder_password), ((issuer_private, issuer_public), issuer_password), _ = role_keys
    key = new_aes_key()
    holder, issuer = wrap_key_for_roles(key, holder_public, issuer_public)
    assert len(holder) == len(issuer) == 384 and holder != issuer
    assert unwrap_key(holder, holder_private, holder_password) == key
    assert unwrap_key(issuer, issuer_private, issuer_password) == key
    with pytest.raises(ValueError):
        unwrap_key(holder, issuer_private, issuer_password)
    with pytest.raises(ValueError):
        unwrap_key(issuer, holder_private, holder_password)


def test_m2_wrong_pem_password_rejected(role_keys):
    (private, public), _ = role_keys[0]
    with pytest.raises(ValueError):
        unwrap_key(wrap_key(new_aes_key(), public), private, "incorrect-test-password")


def test_m2_tampered_wrapped_key_rejected(role_keys):
    (private, public), password = role_keys[0]
    wrapped = bytearray(wrap_key(new_aes_key(), public))
    wrapped[0] ^= 1
    with pytest.raises(ValueError):
        unwrap_key(bytes(wrapped), private, password)


def test_m2_private_pem_encrypted_and_public_fingerprint_matches(role_keys):
    (private, public), password = role_keys[0]
    assert b"BEGIN ENCRYPTED PRIVATE KEY" in private
    loaded_private = serialization.load_pem_private_key(private, password=password.encode())
    loaded_public = serialization.load_pem_public_key(public)
    fmt = (serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    assert sha256_bytes(loaded_private.public_key().public_bytes(*fmt)) == sha256_bytes(loaded_public.public_bytes(*fmt))


def test_m2_pdf_hash_mismatch_detected():
    pdf = (FIXTURES / "diploma.pdf").read_bytes()
    assert len(sha256_bytes(pdf)) == 32
    assert sha256_bytes(pdf) != sha256_bytes(pdf + b"tampered")
