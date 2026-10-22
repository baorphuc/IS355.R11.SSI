# Giao diện chung A/B/C/D — FROZEN v1

Tài liệu này là hợp đồng tích hợp của bốn mảng. A/B/C/D có thể phát triển song song dựa trên đây. Không đổi tên hàm, thứ tự tham số, kiểu dữ liệu hoặc định dạng byte nếu chưa có Pull Request cập nhật đồng thời contract, Python và test.

## 1. ABI contract đã khóa

Các chữ ký tích hợp v1:

```text
registerKey(bytes rsaPublicKey)
createDID(string did)
requestCredential(
  string portraitCid,
  string diplomaCid,
  string metadataCid,
  bytes wrappedKeyForHolder,
  bytes wrappedKeyForIssuer
) returns (uint256 credentialId)
signingDigest(uint256 credentialId, bytes32 docHash) returns (bytes32)
issueCredential(uint256 credentialId, bytes32 docHash, bytes signature)
mintSBT(uint256 credentialId)
revokeCredential(uint256 credentialId)
grantConsent(uint256 credentialId, address verifier, bytes wrappedKeyForVerifier)
revokeConsent(uint256 credentialId, address verifier)
hasAccess(uint256 credentialId, address verifier) returns (bool)
getConsent(uint256 credentialId, address verifier) returns (bool active, bytes wrappedKey)
verifyCredential(uint256 credentialId)
  returns (bool valid, address holder, address issuer, uint8 status, bytes32 docHash)
accessService(uint256 credentialId)
```

Quy ước cố định:

- `credentialId` do Registry sinh tăng dần từ 1; Holder không truyền ID vào request.
- Trạng thái ABI: `NONE=0`, `REQUESTED=1`, `ISSUED=2`, `REVOKED=3`.
- `tokenId` của SBT bằng `credentialId`.
- `accessService` là transaction, không phải view, và phát `ServiceAccessed(user, credentialId)`.
- ABI Python luôn đọc từ `artifacts/`; không giữ bản ABI chép tay.

## 2. Định dạng ciphertext và wrapped key đã khóa

- Mỗi hồ sơ dùng đúng một AES-256 key ngẫu nhiên 32 byte.
- Mỗi file dùng nonce ngẫu nhiên 12 byte riêng, tuyệt đối không tái sử dụng nonce với cùng key.
- AAD cố định là UTF-8 `ssi-demo-v1`.
- Payload IPFS là binary: `nonce[12] || AESGCM(ciphertext || tag[16])` như output của `cryptography.AESGCM.encrypt`.
- Tên file upload: `portrait.jpg.enc`, `diploma.pdf.enc`, `metadata.json.enc`.
- Wrapped key là raw RSA ciphertext bytes, không base64 trước khi truyền vào trường Solidity `bytes`.
- Thuật toán wrap: RSA-OAEP, MGF1-SHA256, SHA256, `label=None`.
- RSA key size demo: 3072 bit; public key là PEM SubjectPublicKeyInfo bytes đăng ký bằng `registerKey`.
- `wrappedKeyForHolder`, `wrappedKeyForIssuer` và `wrappedKeyForVerifier` là cùng AES key được wrap độc lập bằng ba RSA public key khác nhau.
- `docHash` là đúng 32 byte SHA-256 của `diploma.pdf` bản rõ trước mã hóa.

## 3. Thông điệp Issuer ký đã khóa

Solidity và Python cùng tạo:

```text
digest = keccak256(
  abi.encode(
    registryAddress,
    chainId,
    credentialId,
    holderAddress,
    docHash
  )
)
```

Issuer ký đúng 32 byte `digest` theo EIP-191 `personal_sign`/`encode_defunct(primitive=digest)`. Contract kiểm tra `ECDSA.recover(toEthSignedMessageHash(digest), signature) == msg.sender`.

Không ký chuỗi hex, JSON hoặc UTF-8 representation của digest. `registryAddress` và `chainId` nằm trong digest để chống replay giữa contract/mạng.

## 4. Ví Ethereum và RSA key trong demo đã khóa

- Mỗi vai trò dùng một ví Ethereum riêng: Holder, Issuer, Verifier.
- Local: dùng ba account mặc định của Hardhat, chỉ trong mạng chain ID 31337.
- Sepolia: dùng ba ví testnet chuyên dụng, không chứa tài sản thật và không tái sử dụng với mainnet.
- Private key Ethereum chỉ đọc từ `.env` bị Git ignore: `HOLDER_PRIVATE_KEY`, `ISSUER_PRIVATE_KEY`, `VERIFIER_PRIVATE_KEY`. Không nhập hoặc hiển thị private key trên Streamlit.
- Mỗi vai trò có một RSA private key PEM riêng trong `keys/`, mã hóa bằng mật khẩu.
- Mật khẩu PEM chỉ đọc từ `.env`: `HOLDER_RSA_PASSWORD`, `ISSUER_RSA_PASSWORD`, `VERIFIER_RSA_PASSWORD`.
- Tên file thống nhất: `keys/holder_private.pem`, `keys/issuer_private.pem`, `keys/verifier_private.pem`.
- Public PEM có thể lưu trong `keys/*_public.pem` và đăng ký on-chain; private PEM không được upload IPFS hoặc commit Git.
- Streamlit chỉ hiển thị địa chỉ ví/public key fingerprint; không log private key hoặc mật khẩu.

## Ranh giới để làm song song

- A giữ nguyên ABI và event, cung cấp artifact sau compile.
- B hiện thực đúng binary format/AAD/hash/wrap ở trên và cung cấp API Python độc lập.
- C có thể mock CID/wrapped bytes theo format trên để làm UI trước khi B hoàn tất; dùng artifact hiện tại trước khi A deploy Sepolia.
- D viết test theo các vector và chữ ký trên, không chờ UI.

TODO sau khi tích hợp, không chặn phát triển song song: giới hạn kích thước public key/wrapped key, schema metadata JSON nghiệp vụ và UX chọn Issuer. Các mục này không được làm thay đổi interface v1.
