# Test plan tối thiểu

## Tự động hiện có

- Hardhat: request/issue/mint/gate/revoke; chặn transfer; chặn ví thường issue; chặn issuer khác revoke.
- pytest unit: AES-GCM round-trip, nonce khác nhau, RSA-OAEP wrap/unwrap.
- pytest integration: deploy ba contract và chạy Web3.py trên Hardhat local (tự skip nếu node chưa chạy).

## TODO(D) trước nghiệm thu

- Consent grant/revoke và verifier không có consent.
- Sai chữ ký, hash rỗng, duplicate DID/mint, credential không tồn tại.
- IPFS Kubo add/cat ba loại file ciphertext và đối chiếu SHA-256 PDF sau giải mã.
- Sepolia smoke test và lưu tx hash thật. Không đánh dấu đạt trước khi có bằng chứng.
