import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_rsa_keypair(password: str) -> tuple[bytes, bytes]:
    if not password:
        raise ValueError("PEM password must not be empty")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password.encode()),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def save_private_pem(path: Path, private_pem: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(private_pem)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def new_aes_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def encrypt_bytes(plaintext: bytes, key: bytes, associated_data: bytes = b"ssi-demo-v1") -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, associated_data)


def decrypt_bytes(payload: bytes, key: bytes, associated_data: bytes = b"ssi-demo-v1") -> bytes:
    if len(payload) < 29:
        raise ValueError("Invalid AES-GCM payload")
    return AESGCM(key).decrypt(payload[:12], payload[12:], associated_data)


def wrap_key(aes_key: bytes, public_pem: bytes) -> bytes:
    public_key = serialization.load_pem_public_key(public_pem)
    return public_key.encrypt(
        aes_key,
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )


def unwrap_key(wrapped_key: bytes, private_pem: bytes, password: str) -> bytes:
    private_key = serialization.load_pem_private_key(private_pem, password=password.encode())
    return private_key.decrypt(
        wrapped_key,
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )


def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()
