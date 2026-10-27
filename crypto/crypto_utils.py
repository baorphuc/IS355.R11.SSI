import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
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
    if len(payload) < MIN_PAYLOAD_LEN:
        raise ValueError("Invalid AES-GCM payload")
    try:
        return AESGCM(key).decrypt(payload[:12], payload[12:], associated_data)
    except InvalidTag as exc:
        raise ValueError("AES-GCM authentication failed: tag or ciphertext is invalid") from exc


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


__all__ = [
    "generate_rsa_keypair",
    "save_private_pem",
    "new_aes_key",
    "encrypt_bytes",
    "decrypt_bytes",
    "wrap_key",
    "unwrap_key",
    "sha256_bytes",
    "EncryptedPackageError",
    "EncryptedPackage",
    "encrypt_package",
    "decrypt_package",
    "wrap_key_for_roles",
]

# Giao diện FROZEN v1 (docs/2-planning-phase/interfaces.md, §2):
# - Một AES-256 key (32 byte) cho toàn bộ gói hồ sơ.
# - Mỗi file dùng nonce ngẫu nhiên 12 byte, không tái sử dụng với cùng key.
# - AAD cố định là UTF-8 "ssi-demo-v1".
# - Dạng truyền tải (wire format) lên IPFS: nonce[12] || ciphertext || tag[16],
#   đúng đầu ra của cryptography.AESGCM.encrypt. Gói tin KHÔNG chứa khóa RSA
#   đã bọc; wrapped key là trường bytes riêng biệt trên hợp đồng.
PACKAGE_VERSION: int = 1
PACKAGE_ALGORITHM: str = "AES-256-GCM"
AAD_DEFAULT: bytes = b"ssi-demo-v1"
NONCE_LEN: int = 12
TAG_LEN: int = 16
MIN_PAYLOAD_LEN: int = NONCE_LEN + TAG_LEN  # 28 byte (nonce + tag rỗng)


class EncryptedPackageError(ValueError):
    """Lỗi khi đóng gói/giải mã gói tin mã hóa không hợp lệ."""


@dataclass(frozen=True)
class EncryptedPackage:
    """Biểu diễn trong bộ nhớ của một gói mã hóa theo giao diện FROZEN v1.

    `pack()` serialize thành nhị phân `nonce[12] || ciphertext || tag[16]`
    để upload lên IPFS. `unpack()` parse ngược và kiểm tra tính hợp lệ.
    """

    version: int
    algorithm: str
    nonce: bytes
    ciphertext: bytes
    tag: bytes
    aad: bytes = AAD_DEFAULT

    def pack(self) -> bytes:
        """Serialize thành nhị phân đúng định dạng FROZEN v1 để upload IPFS."""
        if self.version != PACKAGE_VERSION:
            raise EncryptedPackageError(f"Phiên bản gói không được hỗ trợ: {self.version}")
        if self.algorithm != PACKAGE_ALGORITHM:
            raise EncryptedPackageError(f"Thuật toán không được hỗ trợ: {self.algorithm}")
        if len(self.nonce) != NONCE_LEN:
            raise EncryptedPackageError(f"Nonce phải dài {NONCE_LEN} byte")
        if len(self.tag) != TAG_LEN:
            raise EncryptedPackageError(f"Thẻ xác thực phải dài {TAG_LEN} byte")
        return self.nonce + self.ciphertext + self.tag

    @classmethod
    def unpack(cls, payload: bytes) -> "EncryptedPackage":
        """Parse nhị phân từ IPFS thành gói có cấu trúc, kiểm tra tính hợp lệ."""
        if not isinstance(payload, (bytes, bytearray)):
            raise EncryptedPackageError("Payload phải là bytes")
        if len(payload) < MIN_PAYLOAD_LEN:
            raise EncryptedPackageError(
                f"Payload quá ngắn (cần ít nhất {MIN_PAYLOAD_LEN} byte, có {len(payload)})"
            )
        nonce = bytes(payload[:NONCE_LEN])
        ciphertext = bytes(payload[NONCE_LEN:-TAG_LEN])
        tag = bytes(payload[-TAG_LEN:])
        if len(nonce) != NONCE_LEN:
            raise EncryptedPackageError("Nonce không đủ 12 byte")
        if len(tag) != TAG_LEN:
            raise EncryptedPackageError("Thẻ xác thực không đủ 16 byte")
        return cls(
            version=PACKAGE_VERSION,
            algorithm=PACKAGE_ALGORITHM,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=tag,
            aad=AAD_DEFAULT,
        )


def encrypt_package(
    plaintext: bytes, key: bytes, associated_data: bytes = AAD_DEFAULT
) -> EncryptedPackage:
    """Mã hóa dữ liệu thô thành gói `EncryptedPackage` (nonce ngẫu nhiên 12 byte)."""
    nonce = os.urandom(NONCE_LEN)
    sealed = AESGCM(key).encrypt(nonce, plaintext, associated_data)
    return EncryptedPackage(
        version=PACKAGE_VERSION,
        algorithm=PACKAGE_ALGORITHM,
        nonce=nonce,
        ciphertext=sealed[:-TAG_LEN],
        tag=sealed[-TAG_LEN:],
        aad=associated_data,
    )


def decrypt_package(
    package: EncryptedPackage, key: bytes, associated_data: bytes = AAD_DEFAULT
) -> bytes:
    """Giải mã và xác thực gói; ném `ValueError` nếu xác thực thất bại."""
    if package.aad != associated_data:
        raise EncryptedPackageError("AAD không khớp giữa gói tin và khóa giải mã")
    try:
        return AESGCM(key).decrypt(package.nonce, package.ciphertext + package.tag, associated_data)
    except InvalidTag as exc:
        raise EncryptedPackageError(
            "AES-GCM xác thực thất bại: bản mã hoặc thẻ xác thực đã bị thay đổi"
        ) from exc


def wrap_key_for_roles(
    aes_key: bytes, holder_public_pem: bytes, issuer_public_pem: bytes
) -> tuple[bytes, bytes]:
    """Bọc cùng một khóa AES riêng cho Holder và Issuer (RSA-OAEP, SHA-256).

    Trả về (wrappedKeyForHolder, wrappedKeyForIssuer) là raw RSA ciphertext bytes,
    không base64, đúng trường `bytes` của hợp đồng.
    """
    return wrap_key(aes_key, holder_public_pem), wrap_key(aes_key, issuer_public_pem)
