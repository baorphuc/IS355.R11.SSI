# Nguồn và thứ tự ưu tiên

Skeleton đối chiếu bốn tài liệu người dùng cung cấp: outline SSI bản 3, Project Charter, architecture mới nhất và WBS 5 Phase.

Nếu không nhất quán, ưu tiên architecture mới nhất. Các chốt đã áp dụng: trạng thái có `NONE`, ID do contract sinh, gate có `credentialId` và event, dùng `hardhat.config.ts`.

Quy tắc một DID cho mỗi ví và nhiều Credential cho mỗi DID được phê duyệt ngày 18/11/2026 trong [DL-02](2-planning-phase/DECISION_LOG_PRE_M1_M2_UPDATED_2026-11-18.md).

Quyết định M1 đã chốt thêm: original Issuer phải còn `ISSUER_ROLE` khi mint/revoke; `IdentitySBT` chỉ bind một Registry; RSA public key đăng ký một lần trong MVP, không rotation/rewrap. Xem Decision Log và `interfaces.md` trước khi thay đổi ABI hoặc luồng tích hợp.

Tài liệu triển khai hiện hành: `README.md` (cài đặt/chạy local), `architecture.md` (luồng), `contracts-spec.md` (quyền/lifecycle) và `crypto-ipfs-m2-api.md` (binary/API crypto-IPFS). `M1_CHECKPOINT_2026-11-18.md` là mốc lịch sử; phần ghi chú sau checkpoint phân biệt kết quả đã có sau ngày đó.

WBS gốc được lưu ở `docs/1-initiation-phase/wbs.xlsx`. Các tài liệu gốc chỉ là nguồn tham chiếu; trạng thái trong WBS không được tự động đổi thành “Đã hoàn thành” bởi skeleton này.
