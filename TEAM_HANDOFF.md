# BÀN GIAO REPOSITORY VÀ PHÂN CÔNG NHÓM

> Dự án: Blockchain SSI trên Ethereum
>
> Phiên bản bàn giao: Skeleton MVP — 22/10/2026
>
> Tài liệu chốt kỹ thuật: `docs/2-planning-phase/interfaces.md` — **FROZEN v1**

## 1. Mục đích của repository

Repository này là nền tảng tối thiểu để bốn thành viên phát triển song song. Đây **chưa phải sản phẩm hoàn chỉnh** và không được báo cáo là đã hoàn thành toàn bộ 12 chức năng. Phạm vi chỉ gồm những nội dung đã chốt trong outline SSI bản 3, Project Charter, architecture mới nhất và WBS 5 Phase.

Khi tài liệu có điểm không nhất quán, cả nhóm ưu tiên `docs/2-planning-phase/architecture.md` và giao diện FROZEN v1.

## 2. Những gì dự án đã có

| Hạng mục | Trạng thái hiện tại | Vị trí |
|---|---|---|
| Cấu hình Solidity 0.8.x, OpenZeppelin 5.x, Hardhat TypeScript | Có, compile được | `hardhat.config.ts`, `package.json` |
| `SSIRegistry` | Có lõi MVP: DID, request, issue, revoke, consent và verify | `contracts/SSIRegistry.sol` |
| `IdentitySBT` | Có mint/burn và chặn chuyển nhượng | `contracts/IdentitySBT.sol` |
| `GatedService` | Có `accessService(credentialId)` và event | `contracts/GatedService.sol` |
| Deploy và cấp role | Có script local/Sepolia | `scripts/deploy.ts`, `scripts/setup-roles.ts` |
| AES-GCM và RSA-OAEP | Có primitive và unit test | `crypto/` |
| IPFS Kubo | Có HTTP client tối thiểu, chỉ nhận file `.enc` | `ipfs/` |
| Web3.py | Có kết nối RPC và nạp artifact cơ bản | `web3_client/` |
| Ba dashboard | Có scaffold Holder/Issuer/Verifier; form hiển thị được | `app/` |
| Giao dịch từ dashboard | **Chưa có**; nút ghi chain đang khóa và ghi rõ TODO(C) | `app/` |
| Hardhat test | Có vòng đời request → issue → mint → gate → revoke và kiểm tra quyền | `test/` |
| pytest | Có unit crypto và integration Web3.py + Hardhat | `tests/` |
| Tài liệu dự án | Có Charter, WBS, architecture, contract spec, key policy, interface và test plan | `docs/` |

Kết quả chạy tại thời điểm bàn giao:

- `npm run compile`: thành công.
- `npm test`: **2 passed**.
- `python -m pytest tests\unit -q`: **2 passed**.
- `python -m pytest tests\integration -q` khi Hardhat node đang chạy: **1 passed**.
- Dashboard Holder khởi động được tại `http://localhost:8501`.

## 3. Những phần chưa hoàn thành

- Chưa nối các nút Streamlit với giao dịch contract thật.
- Chưa hoàn thiện luồng ba file: mã hóa → IPFS → request → Issuer giải mã → issue → Holder/Verifier giải mã.
- Chưa chạy kiểm thử Kubo end-to-end.
- Chưa deploy và lưu bằng chứng giao dịch trên Sepolia.
- Chưa có bộ test đầy đủ cho consent, chữ ký sai, duplicate DID/mint và các trường hợp lỗi.
- Chưa có ảnh, video demo, test report, báo cáo cuối và slide nghiệm thu.

Không tự thêm ZKP, multi-chain, DID deactivation, marketplace, ERC-20 hoặc production custody.

## 4. Phân công bốn thành viên

### A — Smart Contract

Phụ trách chính: `contracts/`, `scripts/`.

Việc cần làm:

1. Đọc `contracts-spec.md` và `interfaces.md` trước khi sửa code.
2. Review ba contract hiện có, bổ sung test biên nhưng giữ nguyên ABI FROZEN v1.
3. Kiểm tra consent, signature, duplicate DID/mint, credential không tồn tại và quyền Issuer.
4. Deploy ba contract lên Sepolia bằng ví testnet riêng.
5. Chạy `setup-roles.ts`, lưu contract address và tx hash làm bằng chứng.
6. Bàn giao artifact sau compile cho C và thông báo rõ network/chain ID.

Hoàn thành khi: contract test đạt, deploy Sepolia thành công, có địa chỉ contract/tx hash và không làm thay đổi interface đã khóa.

### B — Crypto và IPFS

Phụ trách chính: `crypto/`, `ipfs/`.

Việc cần làm:

1. Giữ đúng AES-256-GCM, nonce 12 byte riêng cho từng file và AAD `ssi-demo-v1`.
2. Giữ đúng RSA-OAEP SHA-256, key demo 3072 bit và format ciphertext đã khóa.
3. Hoàn thiện luồng mã hóa ba file giả, upload `.enc` lên Kubo và tải lại.
4. Đối chiếu SHA-256 của PDF bản rõ sau giải mã với `docHash`.
5. Cung cấp hàm Python rõ ràng để C gọi; không đặt logic giao diện trong module crypto/IPFS.
6. Bổ sung test lỗi: sai key, ciphertext bị sửa, nonce/format không hợp lệ và Kubo không chạy.

Hoàn thành khi: round-trip ba file thành công, hash khớp, test lỗi hợp lý và không lộ file gốc/private key.

### C — Web3.py và ba dashboard

Phụ trách chính: `web3_client/`, `app/`.

Việc cần làm:

1. Viết wrapper có kiểu cho từng hàm ABI từ artifact; không chép tay ABI.
2. Nối Holder với `registerKey`, `createDID`, `requestCredential`, consent và revoke consent.
3. Nối Issuer với đọc request, giải mã hồ sơ, tạo chữ ký EIP-191, issue, mint và revoke.
4. Nối Verifier với verify công khai, kiểm tra consent, giải mã khi có quyền và gọi gate.
5. Hiển thị trạng thái chờ/xác nhận/lỗi, transaction hash và dữ liệu kiểm chứng cần thiết.
6. Không cho nhập hoặc hiển thị private key trên Streamlit; key chỉ đọc từ `.env`.
7. Chuẩn bị ảnh giao diện và video demo dự phòng có caption.

Hoàn thành khi: ba dashboard chạy được luồng local end-to-end, lỗi có thông báo rõ, không log bí mật và có thể chuyển sang Sepolia bằng biến môi trường.

### D — Kiểm thử và tài liệu

Phụ trách chính: `test/`, `tests/`, `docs/`.

Việc cần làm:

1. Chuyển các mục TODO trong `docs/4-testing-phase/test-plan.md` thành test hoặc checklist có bằng chứng.
2. Bổ sung test consent grant/revoke, không có consent, chữ ký sai, hash rỗng, duplicate DID/mint và ID không tồn tại.
3. Viết integration test cho Kubo và luồng ba vai trò.
4. Chạy Sepolia smoke test, lưu tx hash/ảnh và không đánh dấu đạt nếu chưa chạy thật.
5. Theo dõi WBS 5 Phase, tổng hợp test report, lỗi còn tồn tại và cách tái hiện.
6. Hoàn thiện báo cáo, slide, hướng dẫn demo và checklist nộp bài.

Hoàn thành khi: có test report tái chạy được, bằng chứng local/Sepolia, WBS phản ánh đúng thực tế và bộ tài liệu nộp thống nhất với code.

## 5. Các chốt kỹ thuật không cần họp lại

Bốn người có thể bắt đầu song song ngay theo `docs/2-planning-phase/interfaces.md`:

- Trạng thái: `NONE=0`, `REQUESTED=1`, `ISSUED=2`, `REVOKED=3`.
- `credentialId` do Registry sinh tăng dần từ 1.
- `requestCredential` có `wrappedKeyForHolder` và `wrappedKeyForIssuer`.
- `tokenId` của SBT bằng `credentialId`.
- Gate dùng `accessService(uint256 credentialId)` và phát `ServiceAccessed`.
- Ciphertext: `nonce[12] || AESGCM(ciphertext || tag[16])`.
- Wrapped key: RSA-OAEP SHA-256 raw bytes.
- `docHash`: SHA-256 đúng 32 byte của PDF bản rõ.
- Issuer ký digest đã khóa bằng EIP-191; không ký JSON hoặc chuỗi hex.
- Local dùng ba account Hardhat; Sepolia dùng ba ví testnet riêng.

Nếu buộc phải đổi một chốt trên, người đề xuất phải tạo Pull Request cập nhật đồng thời contract, Python, test và `interfaces.md`. Không tự đổi riêng trong nhánh cá nhân.

## 6. Cách làm Git để không chờ nhau

Mỗi người tạo nhánh riêng từ `main`:

```text
feature/a-contracts
feature/b-crypto-ipfs
feature/c-web3-ui
test/d-integration-docs
```

Quy trình mỗi công việc:

1. Nhận một Issue có phạm vi và tiêu chí hoàn thành rõ ràng.
2. Commit nhỏ, chỉ sửa thư mục phụ trách nếu không cần tích hợp.
3. Trước khi mở Pull Request, chạy test liên quan và ghi kết quả vào mô tả PR.
4. PR phải nêu: đã làm gì, cách chạy, test nào đạt, phần nào còn TODO và có đổi interface hay không.
5. Ít nhất một thành viên khác review trước khi merge `main`.
6. Không merge code làm đỏ test hiện có.

### Mốc ghép sản phẩm — không phải quan hệ chờ

Bốn người **bắt đầu và phát triển song song ngay từ đầu** dựa trên `interfaces.md` FROZEN v1. Các mốc dưới đây chỉ là lúc ghép kết quả thật vào nhau trước khi merge/nghiệm thu, không có nghĩa người sau phải ngồi chờ người trước:

| Trong lúc làm song song | Khi ghép sản phẩm thật |
|---|---|
| A phát triển/test contract theo ABI đã khóa. | A cập nhật artifact sau compile và địa chỉ contract của môi trường cần test. |
| B phát triển/test crypto và IPFS bằng file giả độc lập. | B cung cấp các hàm Python ổn định để C thay mock bằng dữ liệu thật. |
| C làm ba dashboard bằng artifact hiện có, CID/wrapped key mẫu và local Hardhat. | C nối module thật của B và địa chỉ/artifact cuối của A vào UI. |
| D viết test theo spec, vector và ABI đã khóa; có thể mock UI/module. | D chạy lại test trên bản đã ghép, ghi bằng chứng và báo lỗi có bước tái hiện. |

Vì vậy luồng phối hợp đúng là: **cùng làm song song → mở PR riêng → ghép tại nhánh tích hợp/main → D chạy kiểm tra toàn hệ thống**. Chỉ thay đổi `interfaces.md` mới có thể ảnh hưởng cả bốn người và phải được thống nhất qua Pull Request.

## 7. Chạy project trên Windows PowerShell

Cài đặt một lần:

```powershell
npm install
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Kiểm tra nhanh:

```powershell
npm run compile
npm test
python -m pytest tests\unit -q
```

Chạy local end-to-end, dùng các terminal riêng:

```powershell
npm run node
npm run deploy:local
python -m pytest tests\integration -q
streamlit run app\holder.py
streamlit run app\issuer.py
streamlit run app\verifier.py
```

Xem `README.md` để biết quy trình deploy/cấp role chi tiết.

## 8. An toàn và dữ liệu demo

Tuyệt đối không commit hoặc gửi vào nhóm chat:

- `.env` thật.
- Private key Ethereum.
- RSA private PEM hoặc mật khẩu PEM.
- Keystore, seed phrase hoặc ví có tài sản thật.
- Hồ sơ thật, ảnh cá nhân thật hoặc bằng cấp thật.

Chỉ dùng dữ liệu giả và ví local/Sepolia dành riêng cho đồ án. Trước mỗi commit phải chạy `git status` và kiểm tra lại file staged.

## 9. Definition of Done chung

Một hạng mục chỉ được đánh dấu hoàn thành khi:

- Code chạy được từ hướng dẫn trong repository.
- Có test tự động hoặc bằng chứng kiểm thử phù hợp.
- Không làm hỏng test hiện có.
- Không lộ khóa hoặc dữ liệu cá nhân.
- Không tự mở rộng ngoài phạm vi.
- TODO còn lại được ghi rõ, không dùng dữ liệu giả để tuyên bố thành công.
- PR đã được review và merge vào `main`.
