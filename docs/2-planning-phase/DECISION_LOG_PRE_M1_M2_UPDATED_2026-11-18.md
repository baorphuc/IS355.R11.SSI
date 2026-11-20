# DECISION LOG TRƯỚC MILESTONE 1 & 2

> Ngày rà soát: 17/11/2026
> Baseline: `7227239cff716fc74b5c5ccbe07875be8bb1fc27`
> Trạng thái: DL-02–DL-05 đã được chủ dự án xác nhận ngày 18/11/2026; chưa sửa code/ABI và chưa commit/push GitHub.
> Nguồn đối chiếu: rubric giảng viên trong ảnh người dùng cung cấp; Outline SSI bản 3; `architecture.md`; `contracts-spec.md`; `interfaces.md` FROZEN v1; mã nguồn baseline để nhận diện sai lệch hiện tại.

## Quy ước trạng thái quyết định

- **CONFIRMED BY SOURCE:** tài liệu ưu tiên đã quy định rõ; nhóm chỉ cần xác nhận thực thi.
- **PROPOSED:** PM đã đề xuất phương án nhưng cần người có thẩm quyền phê duyệt.
- **BLOCKED:** chưa đủ thẩm quyền/bằng chứng để kết luận.

## DL-01 — Rubric ERC-20 / NFT Marketplace và SBT

### Nội dung đang quy định

Rubric trong ảnh ghi nguyên văn phần liên quan:

- Tên tiêu chí: **“Tạo & triển khai Token ERC-20 / NFT Marketplace”**.
- Mô tả: **“Tích hợp token vào quy trình (xác minh, thanh toán, chứng nhận)”**.
- Yêu cầu:
  - **“Tạo thành công ít nhất 1 token ERC 20 hoặc NFT contract.”**
  - **“Có tối thiểu 2 nghiệp vụ sử dụng token (VD: cấp, chuyển, xác thực).”**
  - **“Có kiểm thử hoặc demo giao dịch.”**

Outline v3 chọn `IdentitySBT.sol`, kế thừa ERC-721, với các nghiệp vụ mint, xác thực/token-gated access, revoke/burn và cố ý cấm transfer.

### Đánh giá theo nội dung rubric đã được xác nhận

- **Yêu cầu 1 — Token contract:** `IdentitySBT` dựa trên ERC-721 nên về loại hợp đồng là một **NFT contract**. Từ “hoặc” trong yêu cầu cho phép chọn ERC-20 hoặc NFT; do đó không cần bổ sung ERC-20. Rubric không ghi Marketplace là một deliverable riêng trong ba yêu cầu chi tiết.
- **Yêu cầu 2 — Tối thiểu hai nghiệp vụ token:** thiết kế hiện có bốn hành vi có thể dùng làm bằng chứng: mint/cấp SBT; xác thực quyền bằng token-gated access; revoke credential dẫn đến burn/vô hiệu SBT; thử transfer và chứng minh giao dịch bị từ chối vì soulbound. Ví dụ “cấp, chuyển, xác thực” là ví dụ, không bắt buộc phải có chuyển thành công.
- **Yêu cầu 3 — Kiểm thử/demo giao dịch:** baseline có kiểm thử local cơ bản, nhưng chưa có bộ evidence độc lập và demo Sepolia hoàn chỉnh. Vì vậy mới chỉ xác nhận **hướng đáp ứng**, chưa được tuyên bố đã đạt đủ tiêu chí.

SBT là NFT contract nhưng **không phải Marketplace**. Kết luận ở đây chỉ dựa trên ba yêu cầu rubric mà người dùng đã xác nhận; không đổi tên SBT thành Marketplace và không tuyên bố đã xây Marketplace.

### Các phương án

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| A. Dùng SBT/ERC-721 làm NFT contract và chứng minh ≥2 nghiệp vụ | Đúng chữ “hoặc”, đúng use case chứng nhận, không mở rộng | Vẫn phải hoàn tất test/demo thực tế trước khi tuyên bố đạt |
| B. Bổ sung NFT Marketplace | Bám phần tiêu đề theo nghĩa rộng | Không được ba yêu cầu chi tiết bắt buộc; mở rộng phạm vi và tăng rủi ro |
| C. Bổ sung/chuyển sang ERC-20 | Thỏa nhánh ERC-20 | Không cần thiết vì rubric dùng “hoặc”; không phù hợp SSI hiện tại |

### Ảnh hưởng A/B/C/D

- **A:** giữ `IdentitySBT`; harden/test mint, burn khi revoke, non-transferable và Registry-only mint/burn.
- **B:** không ảnh hưởng; không phát sinh token/Marketplace API.
- **C:** hoàn thiện UI mint, trạng thái SBT, token-gated access và kết quả revoke/non-transfer.
- **D:** lập evidence matrix cho cả ba yêu cầu rubric; chạy test/demo độc lập và lưu tx/receipt/log.

### Phương án đề xuất

**A — Sử dụng SBT/ERC-721 để đáp ứng nhánh NFT contract; không bổ sung ERC-20 hoặc Marketplace.** Hai nghiệp vụ chính để chấm là: (1) cấp/mint SBT; (2) xác thực bằng token-gated access. Hai bằng chứng bổ sung là: (3) revoke credential làm burn/vô hiệu SBT; (4) thử transfer phải revert để chứng minh đặc tính soulbound.

### Bằng chứng kỹ thuật phải hoàn thành

| Yêu cầu rubric | Bằng chứng cần có | Trạng thái hiện tại |
|---|---|---|
| 1. Có ít nhất một NFT contract | Source `IdentitySBT`, compile artifact/ABI, inheritance ERC-721, deployment address | Có source/artifact local; chưa có evidence Sepolia cuối |
| 2a. Nghiệp vụ cấp token | Test/demo `mintSBT`, receipt/event, `ownerOf(tokenId) == holder` | Có local happy-path cơ bản; cần D chạy và lưu evidence |
| 2b. Nghiệp vụ xác thực token | Holder có SBT gọi `accessService` thành công và phát event; ví khác thất bại | Có local happy-path một phần; cần positive/negative evidence và UI đúng caller |
| Bổ sung: revoke/burn | Revoke credential, SBT bị burn/vô hiệu, gate thất bại | Có logic/test cơ bản; cần regression và demo |
| Bổ sung: non-transferable | `transferFrom`/`safeTransferFrom` revert | Có test cơ bản; cần log độc lập |
| 3. Test/demo giao dịch | Hardhat test pass; local E2E; Sepolia address/tx/receipt/explorer và ảnh demo | Chưa hoàn tất toàn bộ |

### Trạng thái và người phê duyệt

- Trạng thái: **APPROVED BY PROJECT OWNER — 19/11/2026**. Phê duyệt này chốt phạm vi: dùng `IdentitySBT.sol` theo ERC-721/SBT cho nhánh “ERC-20 hoặc NFT contract”; hai nghiệp vụ chính là Issuer mint SBT cho Holder và Holder dùng SBT qua `GatedService`; revoke credential/burn SBT là nghiệp vụ hỗ trợ. ERC-20 và NFT Marketplace không thuộc MVP.
- Phê duyệt này là quyết định phạm vi của Project Owner, **không** là nghiệm thu triển khai, test, demo local hay Sepolia. A và D vẫn cần xác nhận test/evidence scope; không có xác nhận riêng của giảng viên hoặc toàn bộ nhóm được suy diễn từ quyết định này.
- Xác nhận thêm từ giảng viên: **không còn là dependency bắt buộc** theo nội dung rubric đã được người dùng xác nhận; chỉ cần hỏi thêm nếu giảng viên có hướng dẫn ngoài ba yêu cầu này rằng Marketplace là bắt buộc.

## DL-02 — Một DID có bao nhiêu Credential?

### Nội dung đang quy định

- Outline v3 và Architecture hiện mô tả một ví/một DID/một credential tốt nghiệp. Quyết định chủ dự án ngày 18/11/2026 điều chỉnh cardinality credential: giữ một DID cho mỗi ví nhưng cho phép DID đó có nhiều credential.
- FROZEN v1 dùng `requestCredential(...)` không nhận DID/credentialId; Registry tự tăng `credentialId` và gắn request với Holder/DID của `msg.sender`. Cấu trúc này có thể hỗ trợ nhiều credential cho cùng Holder mà không đổi ABI.
- Baseline contract cần được kiểm tra để xác định guard nào đang giới hạn request lần hai; chưa kết luận source đã tương thích cho đến khi đọc source hiện tại.

### Các phương án

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| A. Một ví = một DID = một credential tốt nghiệp trong demo | Đúng cả Outline v3 và Architecture; demo/test đơn giản | Không hỗ trợ cấp lại hay nhiều bằng; chỉ phù hợp prototype |
| B. Một DID có nhiều credential | Mở rộng thực tế hơn; tận dụng ID tăng dần | Trái phạm vi đã ghi; cần sửa tài liệu và quyết định lifecycle |
| C. Một credential active, cho phép credential mới sau revoke | Có đường cấp lại | Thêm lifecycle/ràng buộc chưa có trong 12 chức năng |

### Ảnh hưởng A/B/C/D

- **A:** thêm ràng buộc/mapping nội bộ và test duplicate request; ABI không cần đổi.
- **B:** không đổi crypto format; chỉ tạo một bộ hồ sơ cho DID demo.
- **C:** khóa nút request sau yêu cầu đầu tiên và hiển thị credentialId hiện tại.
- **D:** thêm test request lần hai phải revert; cập nhật traceability.

### Phương án đề xuất

**A — Một ví chỉ có một DID; DID đó được phép có nhiều credential.** Mỗi lần request hợp lệ tạo một `credentialId` riêng. Chính sách cấp lại sau revoke và giới hạn số credential chưa được mở rộng ngoài quyết định này; không được tự thêm guard “một credential duy nhất” nếu chưa có quyết định mới.

### Trạng thái và người phê duyệt

- Trạng thái: **APPROVED BY PROJECT OWNER — 18/11/2026**. Quyết định này điều chỉnh nội dung Outline/Architecture hiện tại; cần cập nhật hai tài liệu để đồng bộ.
- Review còn lại: A xác nhận cách thực thi không đổi ABI; D xác nhận test.

## DL-03 — Mint/Revoke sau khi Issuer bị thu hồi role

### Nội dung đang quy định

- Outline v3 yêu cầu `require(hasRole(ISSUER_ROLE, msg.sender))` ở `issueCredential`, `revokeCredential`, `mintSBT`; đồng thời Issuer phải là Issuer gốc.
- Architecture cũng ghi `onlyRole(ISSUER_ROLE)` hoặc `require(hasRole(...))` ở phát hành/thu hồi/mint và yêu cầu đúng Issuer.
- Baseline code chỉ kiểm tra current role ở `issueCredential`; `mintSBT` và `revokeCredential` chỉ kiểm tra `credential.issuer == msg.sender`. Đây là sai lệch so với tài liệu.

### Các phương án

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| A. Cả mint và revoke đều yêu cầu current `ISSUER_ROLE` + original issuer | Đúng Outline/Architecture; role revocation có hiệu lực đầy đủ | Khi role bị gỡ, issuer không revoke được cho đến khi Admin cấp lại |
| B. Mint cần current role; original issuer luôn được revoke | Duy trì khả năng thu hồi chứng chỉ | Trái yêu cầu rõ trong Outline; role revocation không cắt toàn bộ quyền |
| C. Original issuer luôn mint/revoke | Khớp baseline hiện tại | Thu hồi role không ngăn thao tác nhạy cảm; trái tài liệu |
| D. Admin emergency revoke | Có cơ chế khẩn cấp | Thêm quyền/logic ngoài phạm vi, có thể đổi interface |

### Ảnh hưởng A/B/C/D

- **A:** thêm role guard cho mint/revoke và test role removed; ABI không đổi.
- **B:** không ảnh hưởng.
- **C:** disable/preflight khi issuer không còn role, hiển thị lỗi rõ.
- **D:** test current role + original issuer cho cả mint/revoke; ghi quy trình Admin cấp lại role nếu cần revoke.

### Phương án đề xuất

**A — Chỉ đúng original issuer mới được mint/revoke credential của mình và phải còn current `ISSUER_ROLE` tại thời điểm gọi.** Issuer khác dù có `ISSUER_ROLE` cũng không được revoke credential do đơn vị khác cấp. Nếu role của Issuer gốc bị thu hồi nhưng cần revoke credential, Admin phải cấp lại role có kiểm soát cho đúng Issuer gốc; không thêm emergency function trong MVP.

### Trạng thái và người phê duyệt

- Trạng thái: **APPROVED BY PROJECT OWNER — 18/11/2026**.
- Review còn lại: A xác nhận guard hiện tại và patch không đổi ABI; D xác nhận test role removed/wrong issuer.

## DL-04 — Registry duy nhất và khả năng thay đổi Registry

### Nội dung đang quy định

- Architecture: **“SSIRegistry là thành phần duy nhất được ủy quyền mint/burn.”**
- Contracts-spec: **“Chưa có nâng cấp contract.”**
- Baseline `IdentitySBT.setRegistry()` có thể gọi nhiều lần và chỉ cấp thêm `REGISTRY_ROLE`; không thu role của Registry cũ. Vì vậy có thể tồn tại nhiều Registry được mint/burn, trái kiến trúc.
- FROZEN v1 không khóa `setRegistry` trong ABI tích hợp nghiệp vụ; sửa internal policy để lần hai revert không làm thay đổi ABI của các hàm tích hợp đã khóa.

### Các phương án

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| A. Bind Registry đúng một lần; muốn đổi phải deploy cặp SBT/Registry mới | Đơn giản, an toàn, đúng “duy nhất” và “không upgrade” | Không thay Registry trên SBT cũ |
| B. Cho thay Registry và thu role Registry cũ | Có khả năng migration | Cần lưu current Registry, sự kiện/quy trình migration và test phức tạp hơn |
| C. Giữ baseline cấp thêm nhiều Registry | Không sửa code | Trái kiến trúc, tăng quyền mint/burn ngoài ý muốn |

### Ảnh hưởng A/B/C/D

- **A:** one-time guard và test lần hai/Registry cũ; deploy script phải gọi đúng một lần.
- **B:** không ảnh hưởng.
- **C:** chỉ đọc address từ deployment; không cung cấp UI đổi Registry.
- **D:** xác minh chỉ Registry đã bind có thể mint/burn; tài liệu redeploy khi cần thay đổi.

### Phương án đề xuất

**A — One-time binding.** Mỗi `IdentitySBT` chỉ có một `SSIRegistry`. MVP không hỗ trợ đổi Registry. Nếu cần thay đổi, deploy một bộ contract mới và cập nhật deployment config; dữ liệu cũ vẫn được đọc trên contract cũ.

### Trạng thái và người phê duyệt

- Trạng thái: **APPROVED BY PROJECT OWNER — 18/11/2026**. MVP không hỗ trợ thay Registry trên deployment SBT đã bind.
- Review còn lại: A kiểm tra mọi đường cấp `REGISTRY_ROLE`/thay Registry; D kiểm thử Registry thứ hai bị từ chối.

## DL-05 — Cập nhật RSA public key và khả năng giải mã credential cũ

### Nội dung đang quy định

- FROZEN v1 có `registerKey(bytes rsaPublicKey)` và RSA-3072, nhưng không định nghĩa update/version/history.
- Contracts-spec ghi rõ **“Chưa có ... key rotation”**.
- Baseline cho phép `registerKey` ghi đè public key bất kỳ lúc nào.
- Wrapped AES key của credential cũ đã được tạo cho public key tại thời điểm request/consent. Đổi public key không tự rewrap dữ liệu cũ; muốn giải mã phải giữ private key cũ.

### Các phương án

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| A. Public key bất biến sau lần đăng ký đầu | Đúng phạm vi “không key rotation”; tránh public key hiện tại gây hiểu nhầm với credential cũ | Mất private key thì không phục hồi; muốn đổi phải dùng ví/identity mới ngoài demo |
| B. Cho ghi đè, bắt buộc giữ private key cũ | Ít sửa code; có thể dùng key mới cho credential mới | On-chain không có version/history; UI khó biết credential dùng key nào; dễ mất khả năng decrypt |
| C. Key versioning/history và rewrap workflow | Đúng bài toán production hơn | Mở rộng lớn, có thể đổi data model/interface, ngoài phạm vi MVP |
| D. Cho đổi chỉ trước request đầu tiên | Linh hoạt trong setup, vẫn bảo vệ credential | Thêm state rule; phức tạp hơn A nhưng không giải quyết rotation thật |

### Ảnh hưởng A/B/C/D

- **A:** với A, lần đăng ký thứ hai revert; ABI giữ nguyên; thêm test.
- **B:** tạo/lưu PEM mã hóa trước khi register; không xoá private key; không xây rotation.
- **C:** UI cảnh báo đăng ký một lần, hiển thị fingerprint và yêu cầu backup local; không có nút update.
- **D:** test duplicate registration; checklist backup/fingerprint; ghi rõ key loss là giới hạn prototype.

### Phương án đề xuất

**A — Public key bất biến sau đăng ký đầu tiên trong MVP.** Private PEM phải được backup an toàn trước khi đăng ký. Credential cũ luôn dùng private key tương ứng với public key đã đăng ký; không có rotation/rewrap trong phạm vi. Nếu mất key, dữ liệu cũ không thể giải mã và đây là giới hạn được công bố.

### Trạng thái và người phê duyệt

- Trạng thái: **APPROVED BY PROJECT OWNER — 18/11/2026**. Không có key rotation/rewrap trong MVP.
- Review còn lại: A/B xác nhận đăng ký một lần, backup/fingerprint UX; C/D review test và cảnh báo key-loss.

## DL-06 — Zero Admin Address Protection

### Nội dung và quyết định xác nhận

Bắt buộc kiểm tra địa chỉ Admin khác địa chỉ zero trong constructor của `IdentitySBT` **trước khi** cấp các quyền quản trị:

```solidity
require(admin != address(0), "zero address");
```

Quy tắc này ngăn contract được triển khai với Admin không hợp lệ và tránh trạng thái triển khai không còn Admin có thể quản trị. Constructor giữ nguyên chữ ký `constructor(address admin)`; không thay đổi ABI v1 hoặc logic Solidity nào khác.

### Bằng chứng kỹ thuật

- `IdentitySBT` thực hiện kiểm tra trước `_grantRole(DEFAULT_ADMIN_ROLE, admin)`.
- Test Round 5 E triển khai `IdentitySBT(ethers.ZeroAddress)` và xác nhận revert đúng `"zero address"`; deployment với Admin hợp lệ vẫn được cấp `DEFAULT_ADMIN_ROLE`.

### Trạng thái và lịch sử xác nhận

- Trạng thái: **APPROVED BY PROJECT OWNER — confirmation recorded 20/11/2026**.
- Ngày 20/11/2026 là ngày Project Owner xác nhận lại và chuẩn hóa hồ sơ DL-06; Decision Log không suy diễn ngày phê duyệt ban đầu hoặc lịch sử khác.

## DL-07 — Phân tách Consent của Verifier và token-gated access của Holder

### Nội dung đang quy định

- `GatedService.accessService(uint256)` kiểm tra `msg.sender` sở hữu SBT có `tokenId == credentialId`, Credential còn `ISSUED` và Holder trong Registry đúng người gọi.
- `hasAccess(credentialId, verifier)` kiểm tra Consent đang hiệu lực cho Verifier cụ thể; luồng ứng dụng dùng quyền này trước khi Verifier unwrap AES key và giải mã tài liệu.

### Phương án

| Phương án | Nội dung | Đánh giá |
|---|---|---|
| A | Giữ Gate cho Holder sở hữu SBT hợp lệ; Verifier verify Credential và truy xuất dữ liệu theo Consent. | Khớp source, giữ ABI/logic MVP. |
| B | Đổi Gate để Verifier trực tiếp truy cập theo Consent. | Cần Change Request, thay đổi logic, test và dashboard; không cần cho MVP. |

### Quyết định đã phê duyệt

**A — Giữ nguyên GatedService hiện tại.** Holder sở hữu Credential/SBT, grant/revoke Consent và gọi Gate khi Credential còn hợp lệ. Verifier xác minh Credential công khai, kiểm tra `hasAccess`, nhận wrapped AES key khi có Consent, rồi tải/giải mã tài liệu. Verifier không cần sở hữu SBT của Holder và không phải người gọi Gate trong MVP. Gate không trực tiếp kiểm tra Consent; không đổi ý nghĩa hay chữ ký `accessService(uint256)`.

### Lý do và trạng thái

- Lý do: phù hợp source Smart Contract và phạm vi MVP; tránh thay đổi ABI và logic hợp đồng không cần thiết.
- Phương án B không triển khai trong MVP; chỉ xem xét khi có Change Request được phê duyệt.
- Trạng thái: **APPROVED BY PROJECT OWNER — 20/11/2026**.

## Bảng tổng hợp quyết định

| ID | Đề xuất chốt | ABI đổi? | Trạng thái | Approval bắt buộc |
|---|---|---:|---|---|
| DL-01 | Dùng SBT/ERC-721 cho nhánh NFT; mint + token-gated là hai nghiệp vụ chính; không làm ERC-20/Marketplace | Không | APPROVED BY PROJECT OWNER — 19/11/2026 | A + D review test/evidence; chưa nghiệm thu |
| DL-02 | Một ví = một DID; một DID có nhiều credential | Không | APPROVED BY PROJECT OWNER — 18/11/2026 | A + D review implementation/test; cập nhật tài liệu |
| DL-03 | Mint/revoke cần current `ISSUER_ROLE` và đúng original issuer; Issuer khác không được revoke | Không | APPROVED BY PROJECT OWNER — 18/11/2026 | A + D review implementation/test |
| DL-04 | Mỗi SBT bind đúng một Registry; không đổi trong MVP | Không | APPROVED BY PROJECT OWNER — 18/11/2026 | A + D review implementation/test |
| DL-05 | RSA public key bất biến sau lần đăng ký đầu; không rotation/rewrap | Không | APPROVED BY PROJECT OWNER — 18/11/2026 | A + B + C/D review UX/test |
| DL-06 | Constructor IdentitySBT từ chối zero Admin trước khi cấp role | Không | APPROVED BY PROJECT OWNER — confirmation recorded 20/11/2026 | Test zero Admin revert; giữ constructor signature |
| DL-07 | Consent dành cho Verifier; token-gated access dành cho Holder sở hữu SBT hợp lệ | Không | APPROVED BY PROJECT OWNER — 20/11/2026 | Đồng bộ tài liệu/demo theo phương án A |

DL-02–DL-05 đã được chủ dự án phê duyệt về mặt chính sách. Approval này cho phép lập patch/test plan, không đồng nghĩa source đã được sửa hoặc nghiệm thu.

## Bảng phê duyệt cần trả lời trước implementation M1

| ID | Câu hỏi phê duyệt chính thức | Hệ quả nếu chấp nhận | Người phải xác nhận |
|---|---|---|---|
| DL-01 | Đã chốt dùng SBT/ERC-721 cho nhánh NFT contract; mint và token-gated là hai nghiệp vụ chính, revoke/burn và non-transferable là bằng chứng bổ sung. | Không phát triển ERC-20/Marketplace; D vẫn nghiệm thu bằng test/demo thực tế | Project Owner phê duyệt 19/11/2026; A + D review evidence |
| DL-02 | Đã chốt: một ví có một DID; DID có thể có nhiều credential. | Mỗi request tạo credentialId riêng; đồng bộ Outline/Architecture; xác định rõ test request lặp hợp lệ. | Chủ dự án đã xác nhận 18/11/2026; A + D review |
| DL-03 | Đã chốt: mint/revoke yêu cầu current `ISSUER_ROLE` và đúng original issuer; Issuer khác không được revoke. | Role bị gỡ thì Issuer gốc phải được Admin cấp lại role có kiểm soát trước khi revoke. | Chủ dự án đã xác nhận 18/11/2026; A + D review |
| DL-04 | Đã chốt: Registry bind một lần; không đổi Registry trên SBT đã bind; mọi đường cấp role phải giữ đúng một Registry. | Nếu bind sai/cần thay đổi thì deploy bộ contract mới; không có recovery trên deployment cũ. | Chủ dự án đã xác nhận 18/11/2026; A + D review |
| DL-05 | Đã chốt: RSA public key bất biến sau lần đăng ký đầu; không rotation/rewrap trong MVP. | Backup private PEM/fingerprint trước register; mất private key thì dữ liệu cũ không giải mã được. | Chủ dự án đã xác nhận 18/11/2026; A + B + C/D review |

## Checklist Go/No-Go cho Milestone 1 và 2

### Bắt buộc trước khi A sửa contract (Milestone 1)

- [x] Chủ dự án xác nhận DL-02: một ví có một DID; một DID có nhiều credential (18/11/2026).
- [x] Chủ dự án xác nhận DL-03: mint/revoke cần current role và đúng original issuer; Issuer khác không được revoke (18/11/2026).
- [x] Chủ dự án xác nhận DL-04: Registry one-time binding, không thay trong MVP (18/11/2026).
- [x] Chủ dự án xác nhận DL-05: RSA public key bất biến sau đăng ký đầu (18/11/2026).
- [x] Project Owner phê duyệt DL-01: SBT/ERC-721 là nhánh NFT cho rubric; không triển khai ERC-20/Marketplace trong MVP (19/11/2026).
- [ ] A trình danh sách patch tối thiểu và test tương ứng; xác nhận không đổi ABI FROZEN v1.
- [ ] D chốt expected result cho duplicate request, role removed, second registry và duplicate key registration.
- [x] Decision Log ghi trạng thái APPROVED BY PROJECT OWNER ngày 18/11/2026; còn chờ review kỹ thuật/test trước khi sửa và nghiệm thu.

### Bắt buộc trước khi B hoàn thiện Crypto/IPFS (Milestone 2)

- [x] Xác nhận RSA-3072 theo FROZEN v1; các mô tả RSA-2048 lịch sử đã được gắn rõ là giới hạn của primitive thấp tầng, không phải cấu hình workflow SSI.
- [ ] Xác nhận không triển khai key rotation/rewrap trong MVP.
- [ ] B xác nhận quy trình tạo PEM, mã hóa mật khẩu, backup và fingerprint trước `registerKey`.
- [ ] B/D thống nhất fixture JPG/PDF/JSON hợp lệ, raw log và evidence format.
- [ ] C nhận API contract của B nhưng chưa tự thay ciphertext/AAD/wrapped-key format.

### Điều kiện nghiệm thu rubric trước Milestone 5/6

- [x] Project Owner phê duyệt DL-01 theo rubric đã xác nhận (19/11/2026).
- [ ] D hoàn thành evidence cho NFT contract, mint, token-gated, revoke/burn, non-transferable và test/demo giao dịch.
- [ ] Chỉ hỏi lại giảng viên nếu xuất hiện hướng dẫn bổ sung mâu thuẫn rằng Marketplace hoặc transfer thành công là bắt buộc.
- [ ] Nếu có yêu cầu mới ngoài rubric hiện tại, PM mở Change Request và đánh giá lại phạm vi; không tự giao A triển khai.

## Kết luận vòng rà soát

- DL-02–DL-05 đã được chủ dự án xác nhận ngày 18/11/2026; đây là quyết định chính sách đã chốt, chưa phải xác nhận source đã đáp ứng.
- DL-02 điều chỉnh Outline/Architecture hiện tại: cần cập nhật tài liệu để thống nhất một ví/một DID/nhiều credential.
- DL-03–DL-05 cần được A kiểm tra source và D rà soát test trước khi triển khai patch. Tất cả dự kiến giữ nguyên ABI FROZEN v1.
- DL-01 được Project Owner phê duyệt ngày 19/11/2026 về phạm vi SBT/ERC-721; chỉ được đánh dấu ACCEPTED sau khi có test/demo evidence.

## Ma trận hành động tiếp theo

| Việc | Owner | Có thể bắt đầu? | Dependency/Gate | Đầu ra |
|---|---|---:|---|---|
| Phê duyệt hướng SBT cho tiêu chí 4 | Project Owner | Hoàn thành | DL-01 APPROVED 19/11/2026 | Phạm vi SBT/ERC-721, chưa phải ACCEPTED |
| Lập test/patch plan contract | A | Đã hoàn thành | Không sửa code | Findings, test matrix và patch plan giữ ABI |
| Sửa contract hardening | A | Chờ kiểm tra source | DL-02–DL-05 đã APPROVED; cần source review + patch/test plan | PR giữ nguyên ABI; chưa commit/push nếu chưa được yêu cầu |
| Chốt evidence scope tiêu chí 4 | D + A | Ngay | DL-01 đã APPROVED; cần evidence độc lập | Mapping contract/mint/gate/revoke/non-transfer/test-demo |
| Chuẩn bị fixture/API/evidence package M2 | B | Đã bàn giao | Chờ D acceptance | `SSI_M2_Crypto_IPFS_Evidence.zip` |
| Tái lập 44/59 test và baseline integrity | D | Bắt đầu ngay | Evidence package + hướng dẫn | Independent test log và kết luận |
| Tái lập Kubo thật upload/retrieve/decrypt | D | Bắt đầu ngay | Kubo 0.43.1/môi trường tương thích | CID/hash/log, file phục hồi, acceptance result |
| Tiếp nhận API handoff M2 | C | Bắt đầu ngay | API handoff; không cần DL-05 để lập plan | API mapping và wrapper plan, không đổi FROZEN v1 |
| Khóa workflow đăng ký RSA key | A + B + C | Chờ | DL-05 APPROVED | Quy tắc một lần đăng ký, backup/fingerprint UX |
| Triển khai test nhiều credential trên một DID | A + D | Chờ source review | DL-02 APPROVED | Request nhiều lần hợp lệ, vẫn chỉ một DID trên ví |
| Triển khai current-role mint/revoke | A + D | Chờ sửa code; test plan làm ngay | DL-03 APPROVED | Role removed tests |
| Triển khai one-time Registry | A + D | Chờ | DL-04 APPROVED | Registry thứ hai bị từ chối |
| Sepolia evidence tiêu chí 4 | A + C + D | Chưa | M1–M4 pass | Address, tx, receipt, explorer, UI evidence |
