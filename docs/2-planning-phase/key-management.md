# Quản lý khóa demo

- Ethereum private key và RSA private key là hai loại khóa khác nhau.
- Chỉ dùng ví local/Sepolia riêng cho đồ án.
- RSA private key phải lưu PEM có mật khẩu; `*.pem`, `.env`, keystore và thư mục `keys/` đã bị Git bỏ qua.
- Mỗi bộ hồ sơ dùng AES-256 key mới; mỗi file dùng nonce AES-GCM 12 byte mới.
- IPFS chỉ nhận file `.enc`; CID và wrapped key vẫn là dữ liệu công khai trên chain.
- Không commit dữ liệu thật, khóa thật hoặc mật khẩu. Module hiện tại là helper cho demo, không phải HSM/production custody.
