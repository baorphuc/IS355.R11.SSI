# BÁO CÁO KIỂM THỰ KUBO THỰC TẾ — MEMBER B: CRYPTO & IPFS

> **Lưu ý:** Đây là báo cáo tổng hợp dựa trên kết quả kiểm thử đã ghi nhận từ phiên làm việc xác minh. Đây không phải stdout nguyên bản của terminal (log gốc không được lưu trong repository). Tất cả con số, CID và hash dưới đây là kết quả thực tế đã được thu thập trong lúc chạy kiểm thử.

## 1. Môi trường kiểm thử

| Mục | Giá trị |
|-----|---------|
| Repository | `D:\UIT\Blockchain\IS355.R11.SSI` |
| Nhánh | `main` |
| Merge commit Member B | `9499a0b` (Merge pull request #1 from baorphuc/feature/b-crypto-ipfs) |
| Kubo executable | `D:\UIT\\Blockchain\kubo\kubo\ipfs.exe` |
| Kubo version | `ipfs version 0.43.1` |
| Kubo API endpoint | `http://127.0.0.1:5001` |
| Trạng thái daemon | Đang chạy (PID 9892) |
| Ngôn ngữ kiểm thử | Python 3.12.10 |

## 2. Fixture giả lập (dữ liệu tổng hợp, không dùng thông tin cá nhân)

| File | Mô tả | Kích thước plaintext |
|------|-------|----------------------|
| `portrait.jpg` | Placeholder ảnh PNG tổng hợp | 57 byte |
| `diploma.pdf` | Placeholder bằng cấp PDF tổng hợp | 55 byte |
| `metadata.json` | Metadata tổng hợp JSON | 71 byte |

## 3. Quy trình kiểm thử (đã thực hiện)

1. Sinh một khóa AES-256 bundle key ngẫu nhiên (32 byte).
2. Mã hóa mỗi file độc lập bằng AES-256-GCM, mỗi file dùng nonce 12 byte khác nhau, AAD = `ssi-demo-v1`.
3. Tính `docHash` = SHA-256 của `diploma.pdf` bản rõ **trước** khi mã hóa.
4. Sinh cặp RSA 3072-bit cho Holder và Issuer (PEM có mật khẩu).
5. Gọi `wrap_key_for_roles()` để bọc cùng khóa AES riêng cho Holder và Issuer (RSA-OAEP, SHA-256, MGF1-SHA256, label=None).
6. Upload ba file `.enc` lên Kubo thật qua `KuboClient.add_bytes()`.
7. Tải lại ba file bằng `KuboClient.cat()` và đối chiếu byte-for-byte với bản upload.
8. Khôi phục khóa AES bằng `unwrap_key()` với RSA private key của Holder.
9. Giải mã ba file, xác thực thẻ AES-GCM, so sánh byte-for-byte với plaintext gốc.
10. Tính SHA-256 của `diploma.pdf` đã giải mã và so sánh với `docHash`.

## 4. CID đã ghi nhận (Kubo thật)

| File | CID | Kích thước `.enc` |
|------|-----|-------------------|
| `portrait.jpg.enc` | `QmaLQamBBWedVk4p4V3PxKGL16BB3Ss9vYVrfkYTn4p1wN` | 85 byte |
| `diploma.pdf.enc` | `QmPoK9KTC8he2pnafcaRWUiUqrUdExgNGP3TrZAJKxNCuu` | 83 byte |
| `metadata.json.enc` | `QmatGBaB9a1Ud1oLPz9ogkRCSnJhEC75ejRcg9MwYhVM9s` | 99 byte |

## 5. Kết quả kiểm thử

### 5.1 Retrieve byte-for-byte
Tất cả 3 file tải lại từ Kubo khớp **hoàn toàn** với bản upload (ciphertext không bị thay đổi).

### 5.2 Decrypt và so sánh plaintext
Tất cả 3 file giải mã thành công, khớp **byte-for-byte** với plaintext gốc.

### 5.3 RSA-OAEP wrap/unwrap trong luồng Kubo thật
- `wrap_key_for_roles(bundle_key, holder_public, issuer_public)` đã được gọi.
- `unwrap_key(wrapped_holder, holder_private, password)` đã gọi thành công, khôi phục đúng bundle key.
- `wrapped_holder != wrapped_issuer` (cả hai là 384 byte, ciphertext khác nhau do RSA-OAEP ngẫu nhiên).

### 5.4 docHash (SHA-256 của diploma.pdf)
```
docHash = 2f4ce5eeb7b97767b2dd4f8a8126882cfd969cd58b9a1a5aa4922d298938c66e
```
SHA-256 của `diploma.pdf` bản rõ (trước mã hóa) **khớp** với SHA-256 của `diploma.pdf` đã giải mã.

### 5.5 Test suite (pytest)
```
41 passed, 1 skipped, 1 warning
```
- `tests/unit/test_crypto.py`: 25 passed
- `tests/unit/test_ipfs.py`: 13 passed (mock Kubo)
- `tests/unit/test_e2e_three_files.py`: 3 passed (mock Kubo)
- `tests/integration/test_hardhat_web3.py`: 1 skipped (Hardhat node chưa chạy — trạng thái dự kiến, tự skip)

Warning duy nhất: `DeprecationWarning` từ `websockets.legacy` (thư viện phụ thuộc của web3), không ảnh hưởng đến crypto/IPFS.

## 6. Kết luận

**BA FILE PASS | docHash matches: True | RSA-OAEP trong luồng Kubo thật: đã gọi và thành công.**

Giới hạn: không có file log stdout gốc được lưu trong repository (script kiểm thử chạy độc lập và đã được xóa sau khi thu thập kết quả). Báo cáo này tổng hợp lại kết quả đã ghi nhận để dùng làm bằng chứng bàn handoff.
