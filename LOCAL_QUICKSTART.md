# Clone và chạy SSI local trên Windows

Hướng dẫn cho máy mới, tạo một phiên local độc lập. Không cần tài khoản Alchemy, ETH Sepolia hoặc key của người khác. Không dùng hướng dẫn này để tiếp tục Credential 1 của phiên Sepolia cũ.

## 1. Chuẩn bị và clone

Cài Git, Node.js/npm theo README, Python 3.11 hoặc 3.12 và Kubo. Cần Internet để tải dependencies và Solidity compiler lần đầu. Mở PowerShell:

```powershell
git clone https://github.com/baorphuc/IS355.R11.SSI.git
cd IS355.R11.SSI
npm ci
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Nếu máy có Python 3.11, thay `py -3.12` bằng `py -3.11`. Nếu lệnh `py` không có trên máy, dùng đường dẫn đầy đủ của Python đã cài, ví dụ `& "C:\duong-dan-Python\python.exe" -m venv .venv`; không chép venv của người khác. Các lệnh Python bên dưới dùng trực tiếp venv, không cần activate hay đổi ExecutionPolicy.

## 2. Cấu hình local trước khi chạy Hardhat

Mở `.env` bằng editor, giữ:

```dotenv
LOCAL_RPC_URL=http://127.0.0.1:8545
SEPOLIA_RPC_URL=
DEPLOYER_PRIVATE_KEY=
IPFS_API_URL=http://127.0.0.1:5001
```

Không khai báo `SSI_RPC_URL` hoặc `SSI_EXPECTED_CHAIN_ID` cho local, kể cả khai báo rỗng. Nếu terminal đang kế thừa cấu hình mạng cũ, mở terminal riêng và bỏ các biến sau trong phiên local:

```powershell
Remove-Item Env:SSI_RPC_URL, Env:SSI_EXPECTED_CHAIN_ID, Env:SEPOLIA_RPC_URL, Env:DEPLOYER_PRIVATE_KEY -ErrorAction SilentlyContinue
```

Kiểm tra nhanh:

```powershell
npm run compile
npm test
.\.venv\Scripts\python.exe -m pytest tests/unit -q
```

Không giữ `DEPLOYER_PRIVATE_KEY=0xREPLACE...` từ mẫu cũ cùng RPC Sepolia không rỗng: Hardhat sẽ báo HH8 dù đang chạy local. Không cần key deployer cho node Hardhat local mặc định.

## 3. Chạy node và gán ba ví local

Trong terminal A ở thư mục repo:

```powershell
npm run node
```

Giữ terminal này chạy. Node mặc định là `127.0.0.1:8545`, chain `31337`. Node in danh sách account và private key test công khai; chỉ dùng chúng trên local, không nạp tài sản thật/testnet vào những ví này.

Điền `.env` theo danh sách node vừa in:

| Account | Vai trò / biến |
| --- | --- |
| #0 | Deployer/admin tự động của script local, không cần điền DEPLOYER_PRIVATE_KEY |
| #1 | ISSUER_PRIVATE_KEY và ISSUER_ADDRESS tương ứng |
| #2 | HOLDER_PRIVATE_KEY |
| #3 | VERIFIER_PRIVATE_KEY và VERIFIER_ADDRESS tương ứng |

Đặt ba password RSA riêng do bạn chọn trong `HOLDER_RSA_PASSWORD`, `ISSUER_RSA_PASSWORD`, `VERIFIER_RSA_PASSWORD`; thay `REPLACE_ME`. Đây là mật khẩu bảo vệ PEM, không phải private key Ethereum. Không gửi `.env` lên Git hoặc nhóm chat.

## 4. Deploy local và cấp quyền

Terminal B tại repo:

```powershell
$env:SSI_DEPLOYMENT_ID = "local_demo_001"
npm run deploy:local
```

Đọc `deployments/localhost.local_demo_001.json`. Chép đúng ba giá trị vào `.env`:

| Trường manifest | Biến .env |
| --- | --- |
| IdentitySBT | IDENTITY_SBT_ADDRESS |
| SSIRegistry | SSI_REGISTRY_ADDRESS |
| GatedService | GATED_SERVICE_ADDRESS |

Ngay sau deploy, dòng `ISSUER_ROLE: FAIL` có thể xuất hiện vì chưa chạy bước cấp role; chưa phải kết quả cuối. Đảm bảo ISSUER_ADDRESS là account #1 rồi chạy trong cùng terminal B; kết quả cần có `ISSUER_ROLE PASS`:

```powershell
npm run roles:local
npx hardhat run scripts/deploy-gated-service.ts --network localhost
```

Lệnh cuối chỉ kiểm tra Gate đã có. Deployment ID chỉ gồm chữ, số, dấu `_`, tối đa 64 ký tự. Nếu manifest đã tồn tại, dùng ID mới cho deployment mới có chủ đích; không xóa/ghi đè để né kiểm tra. Node restart sẽ mất trạng thái chain: deploy mới với ID mới và cập nhật cả ba địa chỉ, không dùng manifest cũ.

## 5. Kubo và RSA

Terminal C: thay đường dẫn dưới đây bằng vị trí Kubo trên máy bạn:

```powershell
$kuboExe = "C:\Tools\kubo\ipfs.exe"
& $kuboExe version
# Chỉ chạy init lần đầu khi chưa có repository Kubo:
& $kuboExe init
& $kuboExe daemon
```

Nếu đã có repository Kubo, bỏ qua `init`, không reset/xóa dữ liệu. Giữ daemon chạy; API cần ở `127.0.0.1:5001`. Kiểm tra bằng terminal khác:

```powershell
curl.exe --noproxy "*" -X POST http://127.0.0.1:5001/api/v0/version
```

Kỳ vọng trả JSON version. Không kết luận Kubo lỗi chỉ dựa vào việc mở URL API trong browser hoặc lỗi của PowerShell Invoke-RestMethod.

Tạo ba keypair RSA tại repo, sau khi điền password:

```powershell
.\.venv\Scripts\python.exe scripts/generate_rsa_keys.py --create holder
.\.venv\Scripts\python.exe scripts/generate_rsa_keys.py --create issuer
.\.venv\Scripts\python.exe scripts/generate_rsa_keys.py --create verifier
```

Script từ chối ghi đè key có sẵn. Sao lưu private PEM, password và fingerprint ở nơi riêng trước khi xác nhận backup trên dashboard. Không xóa hoặc tạo lại key đã đăng ký chỉ để vượt lỗi; public RSA key chỉ đăng ký một lần trong MVP.

## 6. Mở ba dashboard

Mỗi lệnh trong một terminal riêng, đều ở thư mục repo:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/holder.py --server.port 8501
.\.venv\Scripts\python.exe -m streamlit run app/issuer.py --server.port 8502
.\.venv\Scripts\python.exe -m streamlit run app/verifier.py --server.port 8503
```

Mở Holder http://127.0.0.1:8501, Issuer http://127.0.0.1:8502, Verifier http://127.0.0.1:8503. Xác nhận chain 31337 và ví tương ứng trước thao tác. Sau khi sửa `.env`, khởi động lại dashboard để cấu hình có hiệu lực.

Fixture giả có sẵn trong `tests/fixtures/crypto_ipfs_v1/`: `portrait.jpg`, `diploma.pdf`, `metadata.json`.

Luồng demo local mới: đăng ký public key ba vai trò → Holder tạo DID/request với ba file → Issuer giải mã/issue/mint → Verifier public verify, bị chặn trước Consent → Holder grant → Verifier decrypt → Holder revoke → Verifier bị chặn lần mới → Holder Gate. Các thao tác này tạo giao dịch local; không thực hiện trên Sepolia khi chưa được phê duyệt. Dùng credentialId thực tế từ request, không mặc định luôn là 1. Chờ Streamlit rerun hoàn tất sau khi đổi ID.

## 7. Dừng và lựa chọn startup tự động

Với cách chạy thủ công trên: Ctrl+C từng terminal dịch vụ của mình. Không dùng `start-local.ps1 -Stop` để dừng phiên thủ công.

Script tự động là lựa chọn khác, không chạy song song với quy trình thủ công. Nó mặc định dùng RPC **18545**, khác RPC **8545** phía trên. Sau khi cài dependencies, chuẩn bị `.env`, ví, RSA và Kubo repository, có thể dùng trong terminal đã activate venv:

```powershell
.\.venv\Scripts\Activate.ps1
.\start-local.ps1 -Mode Fresh -DeploymentId local_auto_001 -KuboPath "C:\Tools\kubo\ipfs.exe"
# Khi kết thúc phiên do script quản lý:
.\start-local.ps1 -Stop
```

Đường dẫn mặc định Kubo trong script thuộc máy tác giả; luôn truyền `-KuboPath` của máy bạn. Nếu Activate.ps1 bị chính sách máy chặn, dùng quy trình thủ công với Python venv ở trên. Keep chỉ dùng khi node/manifest cùng phiên còn hợp lệ, không dùng sau khi reset node. Cả hai biến chọn mạng `SSI_*` phải vắng mặt khi chạy local.

## 8. Clone không bao gồm phiên Sepolia cũ

`.env`, PEM/key, deployment manifest thật, dữ liệu Kubo và evidence ngoài repo không được tải theo clone. Đây là chủ đích, không phải yêu cầu đưa secret lên GitHub. Để xem hoặc tiếp tục deployment Sepolia cũ cần kế hoạch riêng về RPC, địa chỉ/manifest công khai, quyền ví, RSA key và khả năng truy xuất ciphertext. Không chia sẻ private key cá nhân để giúp thành viên chạy local.

Kiểm chứng ngày 22/11/2026: clone GitHub main `2884d209` vào thư mục riêng rồi áp dụng bốn file onboarding đang review; cài mới node_modules/venv, tạo .env/RSA/Kubo repository mới. Trên máy Windows hiện có Node 24.11.1, Python 3.12.10 và Kubo 0.43.1: compile, 42 Hardhat tests, 84 Python unit tests, TypeScript, deploy/cấp role/verify local đều đạt. Ba fixture mã hóa upload/retrieve/decrypt đúng qua Kubo chạy offline riêng. Ba dashboard qua Streamlit AppTest không có exception/error, kết nối chain 31337 và dừng tại bước đăng ký RSA; ba health endpoint trả HTTP 200.

Đây là kiểm tra clone sạch trên cùng máy, có thể dùng cache tải dependencies/compiler; không phải máy Windows mới hoàn toàn, kiểm tra giao diện bằng mắt hoặc lượt E2E UI đầy đủ. Không dùng dữ liệu/key của phiên Sepolia. Không thử nhánh startup tự động trong lượt này.

`npm ci` thành công nhưng npm audit báo 22 mục (11 low, 4 moderate, 7 high); chưa đánh giá khả năng ảnh hưởng thực tế. Không tự chạy `npm audit fix` làm đổi dependency ngoài phạm vi onboarding. Có một cảnh báo deprecation websockets trong pytest. Các mục này không làm bước khởi chạy thử thất bại, nhưng không được diễn giải thành chứng nhận bảo mật.
