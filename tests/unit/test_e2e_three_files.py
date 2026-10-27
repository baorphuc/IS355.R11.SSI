"""Kiểm thử end-to-end luồng ba file hồ sơ (giả Kubo, dữ liệu tổng hợp)."""

import pytest
from pathlib import Path

from crypto.crypto_utils import (
    EncryptedPackage,
    decrypt_package,
    encrypt_package,
    generate_rsa_keypair,
    new_aes_key,
    sha256_bytes,
    unwrap_key,
    wrap_key_for_roles,
)
from ipfs.kubo_client import KuboClient

RSA_PASSWORD = "demo-password"

SAMPLES = {
    "portrait.jpg": b"\x89PNG\r\n\x1a\n synthetic portrait image bytes (JPG placeholder)",
    "diploma.pdf": b"%PDF-1.4\n synthetic diploma certificate content for SSI",
    "metadata.json": b'{"holder":"demo-student","degree":"Bachelor of Science","issuer":"UIT"}',
}


def test_three_file_e2e_encrypt_upload_retrieve_decrypt_verify(tmp_path, fake_kubo):
    """Toàn luồng: mã hóa 3 file → upload IPFS → tải lại → giải mã → xác minh hash."""
    client, _store = fake_kubo

    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    enc_dir = tmp_path / "enc"
    enc_dir.mkdir()

    # 1. Tạo ba file mẫu tổng hợp (dữ liệu giả, không dùng file thật)
    plaintexts: dict[str, bytes] = {}
    for name, data in SAMPLES.items():
        (samples_dir / name).write_bytes(data)
        plaintexts[name] = data

    # 2. docHash là SHA-256 của diploma.pdf bản rõ TRƯỚC khi mã hóa
    diploma_plaintext = plaintexts["diploma.pdf"]
    doc_hash = sha256_bytes(diploma_plaintext)
    assert len(doc_hash) == 32

    # 3. Một khóa AES-256 ngẫu nhiên cho toàn bộ gói hồ sơ
    bundle_key = new_aes_key()
    assert len(bundle_key) == 32

    # 4. Sinh cặp RSA cho Holder và Issuer (3072-bit, PEM có mật khẩu)
    holder_private, holder_public = generate_rsa_keypair(RSA_PASSWORD)
    issuer_private, issuer_public = generate_rsa_keypair(RSA_PASSWORD)

    # 5. Bọc cùng khóa AES riêng cho Holder và Issuer (RSA-OAEP, SHA-256)
    wrapped_holder, wrapped_issuer = wrap_key_for_roles(
        bundle_key, holder_public, issuer_public
    )
    assert wrapped_holder != wrapped_issuer

    # 6. Mã hóa mỗi file độc lập, nonce 12 byte khác nhau, lưu *.enc
    nonces: set[bytes] = set()
    cids: dict[str, str] = {}
    for name, data in plaintexts.items():
        pkg = encrypt_package(data, bundle_key)
        assert pkg.nonce not in nonces, f"Nonce tái sử dụng cho file {name}"
        nonces.add(pkg.nonce)

        enc_path = enc_dir / f"{name}.enc"
        enc_path.write_bytes(pkg.pack())

        # 7. Chỉ upload file đã mã hóa lên Kubo, nhận CID
        cid = client.add_bytes(enc_path.read_bytes(), enc_path.name)
        cids[name] = cid

    assert len(cids) == 3
    assert len(nonces) == 3

    # 8. Tải lại mỗi file, kiểm tra ciphertext khớp byte-for-byte với bản upload
    for name in plaintexts:
        uploaded = (enc_dir / f"{name}.enc").read_bytes()
        retrieved = client.cat(cids[name])
        assert retrieved == uploaded, f"Ciphertext không khớp cho {name}"

    # 9. Khôi phục khóa AES bằng RSA private key của Holder (quy tắc bọc khóa)
    recovered_key = unwrap_key(wrapped_holder, holder_private, RSA_PASSWORD)
    assert recovered_key == bundle_key

    # 10. Giải mã mỗi file, xác thực thẻ AES-GCM, so sánh byte-for-byte với nguồn
    for name, data in plaintexts.items():
        enc_path = enc_dir / f"{name}.enc"
        pkg = EncryptedPackage.unpack(enc_path.read_bytes())
        decrypted = decrypt_package(pkg, recovered_key)
        assert decrypted == data, f"Giải mã không khớp nguồn cho {name}"

    # 11. Tính SHA-256 của diploma.pdf đã giải mã và so sánh với docHash
    decrypted_pdf = decrypt_package(
        EncryptedPackage.unpack((enc_dir / "diploma.pdf.enc").read_bytes()),
        recovered_key,
    )
    assert sha256_bytes(decrypted_pdf) == doc_hash, "docHash diploma.pdf không khớp"


def test_e2e_wrong_private_key_cannot_unwrap(tmp_path, fake_kubo):
    """Khóa RSA không đúng không thể khôi phục khóa AES."""
    client, _ = fake_kubo
    bundle_key = new_aes_key()
    holder_private, holder_public = generate_rsa_keypair(RSA_PASSWORD)
    issuer_private, issuer_public = generate_rsa_keypair(RSA_PASSWORD)
    wrapped_holder, wrapped_issuer = wrap_key_for_roles(
        bundle_key, holder_public, issuer_public
    )
    wrong_private, _ = generate_rsa_keypair("wrong-password")
    with pytest.raises(Exception):
        unwrap_key(wrapped_holder, wrong_private, "wrong-password")


def test_e2e_tampered_retrieved_ciphertext_fails_decryption(tmp_path, fake_kubo):
    """Bản mã bị sửa sau khi tải về phải khiến giải mã thất bại."""
    client, store = fake_kubo
    bundle_key = new_aes_key()
    data = SAMPLES["diploma.pdf"]
    pkg = encrypt_package(data, bundle_key)
    cid = client.add_bytes(pkg.pack(), "diploma.pdf.enc")

    # Thông dịch viên tấn công: sửa byte trong store (giả mạo nội dung IPFS)
    tampered = bytearray(store[cid])
    tampered[-1] ^= 0xFF
    store[cid] = bytes(tampered)

    retrieved = client.cat(cid)
    tampered_pkg = EncryptedPackage.unpack(retrieved)
    with pytest.raises(Exception):
        decrypt_package(tampered_pkg, bundle_key)
