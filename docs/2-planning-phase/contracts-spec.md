# Đặc tả contract đã chốt cho skeleton

Nguồn ưu tiên: `architecture.md` mới nhất. Khi outline/WBS khác architecture, skeleton dùng:

- `CredentialStatus`: `NONE=0`, `REQUESTED=1`, `ISSUED=2`, `REVOKED=3`.
- `credentialId` do `SSIRegistry` sinh tăng dần, bắt đầu từ 1.
- `requestCredential` nhận ba CID ciphertext, `wrappedKeyForHolder` và `wrappedKeyForIssuer`.
- Digest Issuer: `keccak256(abi.encode(registry, chainId, credentialId, holder, docHash))`, sau đó ký EIP-191.
- `IdentitySBT.tokenId == credentialId`; chỉ Registry mint/burn; transfer bị chặn.
- `GatedService.accessService(uint256 credentialId)` là transaction và phát `ServiceAccessed`.

## Những gì đã implement thật

Vòng đời credential, `ISSUER_ROLE`, chữ ký EIP-191, mint/burn SBT, chặn transfer, consent hiện hành và gate/event.

## Giới hạn có chủ ý

- DID là chuỗi mô phỏng, chưa phải W3C DID method.
- Consent không thể thu hồi ciphertext/key đã xuất hiện trong lịch sử chain.
- Chưa có nâng cấp contract, key rotation, DID deactivation, ZKP hoặc production key custody.
- Chưa verify source Etherscan; chỉ có script deploy Sepolia.
