# Đặc tả contract đã chốt cho skeleton

Nguồn ưu tiên: `architecture.md` mới nhất. Khi outline/WBS khác architecture, skeleton dùng:

- `CredentialStatus`: `NONE=0`, `REQUESTED=1`, `ISSUED=2`, `REVOKED=3`.
- Mỗi ví đăng ký đúng một DID. Một DID có thể có nhiều Credential. Mỗi lần gọi `requestCredential()` hợp lệ, Registry sinh một `credentialId` mới. ID tăng dần từ 1.
- `requestCredential` nhận ba CID ciphertext, `wrappedKeyForHolder` và `wrappedKeyForIssuer`.
- Digest Issuer: tạo đúng `keccak256(abi.encode(registryAddress, chainId, credentialId, holderAddress, docHash))`, sau đó áp dụng EIP-191 `personal_sign` trên 32 byte digest thô (không ký chuỗi hex/JSON).
- `IdentitySBT.tokenId == credentialId`; chỉ Registry đã bind một lần mới mint/burn; transfer bị chặn.
- `hasAccess(credentialId, verifier)` biểu diễn consent đang hiệu lực cho Verifier đó; đây là điều kiện để ứng dụng hỗ trợ Verifier truy xuất/giải mã dữ liệu, không phải điều kiện Gate kiểm tra trực tiếp.
- `GatedService.accessService(uint256 credentialId)` là transaction và phát `ServiceAccessed`; chỉ ví đang sở hữu SBT `tokenId == credentialId` và là Holder của Credential `ISSUED` gọi được. Verifier không gọi Gate trong MVP.

## Những gì đã implement thật

Vòng đời credential, `ISSUER_ROLE`, chữ ký EIP-191, mint/burn SBT, chặn transfer, consent hiện hành và gate/event. Mint/revoke yêu cầu caller vừa có `ISSUER_ROLE` hiện tại vừa là original Issuer lưu trên credential. Sau revoke, SBT tương ứng bị burn và Gate từ chối truy cập.

`registerKey(bytes)` chỉ cho phép public RSA key đầu tiên của ví. Key này bất biến trong MVP; contract không lưu private PEM, key version hoặc lịch sử rewrap. `grantConsent` yêu cầu caller là Holder của Credential, Credential đang `ISSUED`, Verifier khác địa chỉ zero và wrapped key không rỗng. `revokeConsent` chỉ kiểm tra caller là Holder của Credential rồi tắt consent hiện hành; hàm này không yêu cầu trạng thái `ISSUED` và không thể xóa bytes đã xuất hiện trong lịch sử chain.

`IdentitySBT.setRegistry` chỉ bind một Registry. Không hỗ trợ thay Registry hoặc cấp Registry thứ hai trong MVP; cấu hình sai cần deployment mới. Các policy trên giữ nguyên chữ ký ABI FROZEN v1.

## Giới hạn có chủ ý

- DID là chuỗi mô phỏng, chưa phải W3C DID method.
- Consent không thể thu hồi ciphertext/key đã xuất hiện trong lịch sử chain.
- Chưa có nâng cấp contract, key rotation, DID deactivation, ZKP hoặc production key custody.
- Chưa verify source Etherscan; chỉ có script deploy Sepolia.
