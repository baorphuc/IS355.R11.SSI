<p align="center">
  <a href="https://www.uit.edu.vn/" title="Trường Đại học Công nghệ Thông tin">
    <img src="https://i.imgur.com/WmMnSRt.png" alt="Trường Đại học Công nghệ Thông tin | University of Information Technology">
  </a>
</p>

<h1 align="center"><b>IS355.R11 — BLOCKCHAIN SSI TRÊN ETHEREUM</b></h1>

<p align="center">
  Nền tảng Self-Sovereign Identity tối thiểu phục vụ đồ án học phần
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Solidity-0.8.x-363636?logo=solidity" alt="Solidity 0.8.x">
  <img src="https://img.shields.io/badge/OpenZeppelin-5.x-4E5EE4?logo=openzeppelin" alt="OpenZeppelin 5.x">
  <img src="https://img.shields.io/badge/Hardhat-TypeScript-F7DF1E?logo=typescript" alt="Hardhat TypeScript">
  <img src="https://img.shields.io/badge/Python-Web3.py-3776AB?logo=python&logoColor=white" alt="Python Web3.py">
  <img src="https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
</p>

> [!IMPORTANT]
> Đây là **MVP phục vụ học tập**, chưa phải hệ thống SSI/Verifiable Credential hoàn chỉnh. Luồng local Holder/Issuer/Verifier, mã hóa/IPFS và dashboard đã có implementation/test tương ứng; Sepolia và bằng chứng nghiệm thu cuối vẫn chưa được tuyên bố hoàn thành.

---

## Mục lục

- [1. Giới thiệu](#1-giới-thiệu)
- [2. Trạng thái hiện tại](#2-trạng-thái-hiện-tại)
- [3. Kiến trúc tổng quan](#3-kiến-trúc-tổng-quan)
- [4. Công nghệ sử dụng](#4-công-nghệ-sử-dụng)
- [5. Cấu trúc repository](#5-cấu-trúc-repository)
- [6. Cài đặt trên Windows](#6-cài-đặt-trên-windows)
- [7. Chạy và kiểm thử](#7-chạy-và-kiểm-thử)
- [8. Phân công nhóm](#8-phân-công-nhóm)
- [9. Tài liệu dự án](#9-tài-liệu-dự-án)
- [An toàn và giới hạn phạm vi](#an-toàn-và-giới-hạn-phạm-vi)

---

## 1. Giới thiệu

Repository xây dựng nền tảng tối thiểu cho đồ án **Blockchain SSI trên Ethereum**, trong đó:

- **Holder** đăng ký DID mô phỏng và yêu cầu cấp credential.
- **Issuer** kiểm tra hồ sơ, ký và phát hành credential.
- **Verifier** xác minh trạng thái công khai; khi Holder đã cấp consent, Verifier kiểm tra `hasAccess`, rồi tải và giải mã hồ sơ.
- Hồ sơ nhạy cảm được mã hóa ngoài chuỗi; blockchain chỉ lưu hash, CID, chữ ký và trạng thái cần thiết.
- `IdentitySBT` biểu diễn credential không chuyển nhượng.
- `GatedService` minh họa dịch vụ chỉ cho Holder sở hữu SBT và có credential hợp lệ truy cập; Gate không kiểm tra consent của Verifier.

Thiết kế bám theo bốn tài liệu đã thống nhất: outline SSI bản 3, Project Charter, architecture mới nhất và WBS 5 Phase. Nếu có điểm không nhất quán, repository ưu tiên architecture mới nhất.

Giao diện tích hợp giữa bốn mảng đã được khóa tại [`docs/2-planning-phase/interfaces.md`](docs/2-planning-phase/interfaces.md) — **FROZEN v1**. Bốn thành viên có thể phát triển song song dựa trên tài liệu này.

---

## 2. Trạng thái hiện tại

| Hạng mục | Trạng thái | Ghi chú |
|---|:---:|---|
| Ba smart contract | ✅ | Hardening M1 và test Hardhat hiện có |
| Vòng đời `REQUESTED → ISSUED → REVOKED` | ✅ | Đã test bằng Hardhat |
| Identity SBT không chuyển nhượng | ✅ | Mint/burn và chặn transfer |
| Token-gated service | ✅ | `accessService(credentialId)` phát event |
| AES-GCM và RSA-OAEP | ✅ | Primitive và unit test đã có |
| Web3.py kết nối Hardhat local | ✅ | Có integration test |
| IPFS Kubo client | ✅ | Đã kiểm thử Kubo thật (0.43.1): upload/retrieve 3 file .enc, byte-for-byte khớp, docHash matches, RSA-OAEP wrap/unwrap trong luồng thực. Xem `evidence/member_b_kubo_e2e.md`. |
| Ba dashboard Streamlit | ✅ | Holder, Issuer, Verifier thực thi được trong môi trường sạch local; không thay cho evidence Sepolia |
| Deploy Sepolia | ⬜ | Chưa chạy và chưa có tx hash thật |
| Báo cáo/slide/video nghiệm thu | ⬜ | Nhóm tiếp tục thực hiện theo WBS |

Mốc regression M1 gần nhất (local/isolated environment):

```text
Hardhat/TypeScript    39 tests passing (Solidity contract và deployment workflow)
pytest Python unit    66 tests passing (crypto, key lifecycle và helper Python)
Web3.py integration   1 test passing (Python với blockchain local khi node đáp ứng yêu cầu)
```

Quy ước trạng thái credential:

```text
NONE = 0  →  REQUESTED = 1  →  ISSUED = 2  →  REVOKED = 3
```

---

## 3. Kiến trúc tổng quan

```mermaid
flowchart LR
    H[Holder Dashboard] --> W[Web3.py Client]
    I[Issuer Dashboard] --> W
    V[Verifier Dashboard] --> W
    W --> R[SSIRegistry]
    R --> S[IdentitySBT]
    R --> G[GatedService]
    H --> C[AES-GCM / RSA-OAEP]
    I --> C
    V --> C
    C --> P[(IPFS Kubo)]
```

### Các nguyên tắc đã khóa

- Mỗi ví đăng ký đúng một DID. Một DID có thể có nhiều Credential. Mỗi lần gọi `requestCredential()` hợp lệ, Registry sinh một `credentialId` mới. ID tăng dần từ `1`.
- `requestCredential` chứa `wrappedKeyForHolder` và `wrappedKeyForIssuer`.
- `tokenId` của SBT bằng `credentialId`.
- `docHash` là SHA-256 của file PDF bản rõ trước mã hóa.
- Mỗi hồ sơ dùng một AES-256 key; mỗi file có nonce 12 byte riêng.
- AES key được wrap độc lập bằng RSA-3072/OAEP SHA-256 cho từng vai trò; public key là PEM SPKI và fingerprint là SHA-256 của DER SubjectPublicKeyInfo.
- Private PEM không lên chain. Public key chỉ đăng ký một lần trong MVP; phải backup private PEM và kiểm tra fingerprint trước khi đăng ký, vì không có rotation/rewrap.
- Issuer tạo `digest = keccak256(abi.encode(registryAddress, chainId, credentialId, holderAddress, docHash))`, sau đó áp dụng EIP-191 `personal_sign` trên đúng 32 byte digest thô; không ký chuỗi hex hoặc JSON.
- Contract không giải mã dữ liệu; crypto và IPFS được xử lý bằng Python.

Chi tiết đầy đủ nằm trong [`architecture.md`](docs/2-planning-phase/architecture.md) và [`interfaces.md`](docs/2-planning-phase/interfaces.md).

---

## 4. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Smart contract | Solidity 0.8.x, OpenZeppelin Contracts 5.x |
| Phát triển blockchain | Hardhat, TypeScript, Ethers.js |
| Blockchain local/testnet | Hardhat Network, Ethereum Sepolia |
| Backend adapter | Python, Web3.py, eth-account |
| Mã hóa | cryptography: AES-256-GCM, RSA-3072/OAEP SHA-256 |
| Lưu trữ ngoài chuỗi | IPFS Kubo HTTP API |
| Giao diện | Streamlit — Holder, Issuer, Verifier |
| Kiểm thử | Hardhat/Chai, pytest + Web3.py |

---

## 5. Cấu trúc repository

```text
ssi-ethereum-skeleton/
├── contracts/                  # A — SSIRegistry, IdentitySBT, GatedService
├── scripts/                    # A — Deploy contract và cấp ISSUER_ROLE
├── crypto/                     # B — AES-GCM, RSA-OAEP và hashing
├── ipfs/                       # B — Kubo HTTP client
├── web3_client/                # C — RPC, artifact và contract adapter
├── app/                        # C — Holder, Issuer, Verifier dashboard
├── test/                       # D — Hardhat contract tests
├── tests/                      # D — pytest unit và integration
├── docs/                       # Charter, WBS, architecture, spec và test plan
├── deployments/               # Địa chỉ local/testnet; JSON thật bị Git ignore
├── .env.example               # Mẫu biến môi trường, không chứa khóa thật
├── TEAM_HANDOFF.md             # Bàn giao và phân công chi tiết
├── hardhat.config.ts
├── package.json
└── requirements.txt
```

---

## 6. Cài đặt trên Windows

### 6.1 Yêu cầu

- Node.js 20 LTS và npm.
- Python 3.11 hoặc 3.12.
- Git.
- IPFS Kubo nếu phát triển phần IPFS.

### 6.2 Cài dependencies

Mở PowerShell tại thư mục repository:

```powershell
npm install
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`requirements.txt` bao gồm `python-dotenv` và các dependency fixture của dashboard. Chỉ điền private key của account Hardhat local hoặc ví Sepolia dành riêng cho đồ án. Không sử dụng ví chứa tài sản thật.

---

## 7. Chạy và kiểm thử

### 7.1 Compile và test nhanh

```powershell
npm run compile
npm test
python -m pytest tests\unit -q
```

### 7.2 Hardhat local và integration test

Terminal 1:

```powershell
npm run node
```

Terminal 2:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests\integration -q
```

Integration test sẽ `skip` có giải thích nếu artifact chưa được compile hoặc Hardhat local chưa chạy.

### 7.3 Deploy local và cấp role

Giữ Hardhat node đang chạy, sau đó mở terminal khác:

```powershell
# Dùng ID mới cho mỗi deployment có chủ đích; không tái dùng manifest cũ.
$env:SSI_DEPLOYMENT_ID = "local-demo-001"
npm run deploy:local

# Chép 3 địa chỉ từ manifest vào .env: IDENTITY_SBT_ADDRESS,
# SSI_REGISTRY_ADDRESS, GATED_SERVICE_ADDRESS; rồi đặt ISSUER_ADDRESS.
npm run roles:local

# Helper chỉ kiểm tra Gate đã được deploy/link đúng, không deploy Gate thứ hai.
npx hardhat run scripts/deploy-gated-service.ts --network localhost
```

Quy trình deploy theo thứ tự `IdentitySBT → SSIRegistry → setRegistry → GatedService`.
Script kiểm tra chain ID, signer, bytecode, liên kết contract và role trước khi ghi manifest.
Manifest có deployment ID, transaction/block hash và genesis hash; script từ chối ghi đè manifest mặc định. Không sửa hoặc tái dùng manifest của chain khác.

### 7.4 Chạy ba dashboard

Chạy mỗi dashboard ở một terminal riêng:

```powershell
python -m streamlit run app\holder.py --server.port 8501
python -m streamlit run app\issuer.py --server.port 8502
python -m streamlit run app\verifier.py --server.port 8503
```

Trước khi dùng dashboard, `.env` phải có RPC, ba địa chỉ contract từ manifest và password RSA theo role. Dashboard tạo/kiểm tra key pair theo role, chỉ cho đăng ký public key khi người vận hành đã xác nhận backup private PEM và fingerprint. Không dán PEM, password hoặc private key vào giao diện/log.

### 7.5 IPFS Kubo

```powershell
ipfs init
ipfs daemon
```

`ipfs/kubo_client.py` chỉ nhận file `.enc`. IPFS không phải private storage; tính bí mật phụ thuộc vào AES/RSA và cách quản lý khóa.

#### Cách sử dụng nhanh (Crypto & IPFS - Member B)

```python
from crypto.crypto_utils import (
    new_aes_key, generate_rsa_keypair, encrypt_package, decrypt_package,
    sha256_bytes, wrap_key_for_roles, unwrap_key,
)
from ipfs.kubo_client import KuboClient

# 1. Sinh khóa AES-256 cho gói hồ sơ và cặp RSA-3072 Holder/Issuer
aes_key = new_aes_key()
holder_priv, holder_pub = generate_rsa_keypair("mat-khau-pem")
issuer_priv, issuer_pub = generate_rsa_keypair("mat-khau-pem")

# 2. docHash = SHA-256 của diploma.pdf bản rõ (trước mã hóa)
doc_hash = sha256_bytes(diploma_pdf_bytes)

# 3. Mã hóa mỗi file độc lập, nonce 12 byte khác nhau; lưu *.enc
pkg = encrypt_package(file_bytes, aes_key)
enc_bytes = pkg.pack()  # wire format: nonce[12] || ciphertext || tag[16]

# 4. Bọc khóa AES riêng cho Holder và Issuer (RSA-OAEP, SHA-256)
wrapped_holder, wrapped_issuer = wrap_key_for_roles(aes_key, holder_pub, issuer_pub)

# 5. Upload chỉ file đã mã hóa lên Kubo, tải lại bằng CID
client = KuboClient()
cid = client.add_bytes(enc_bytes, "diploma.pdf.enc")
retrieved = client.cat(cid)  # bytes bằng hệt bản upload

# 6. Khôi phục khóa AES bằng private key Holder, giải mã và xác thực
aes_key_again = unwrap_key(wrapped_holder, holder_priv, "mat-khau-pem")
plaintext = decrypt_package(pkg, aes_key_again)
assert sha256_bytes(plaintext) == doc_hash  # nếu là diploma.pdf
```

- Wire format v1 là **binary cố định**: `nonce[12] || ciphertext || tag[16]`.
  Gói không chứa RSA wrapped key hoặc AAD; AAD luôn là UTF-8 `ssi-demo-v1`.
  `EncryptedPackage.unpack()` kiểm tra kích thước tối thiểu trước khi giải mã,
  còn `pack()` chỉ chấp nhận đúng phiên bản/thuật toán/AAD v1.
- AES key phải đúng 32 byte. RSA-OAEP dùng MGF1-SHA256, SHA256 và `label=None`;
  wrapped key là raw RSA ciphertext bytes, không base64.
- Không upload dữ liệu thô, khóa riêng RSA hoặc mật khẩu lên IPFS/Git.
- Unit test IPFS dùng giả Kubo (mock); evidence M2 đã có kiểm thử Kubo thật. Muốn tái lập kiểm thử thật cần `ipfs daemon` tại `127.0.0.1:5001`.

Tạo PEM theo luồng ứng dụng bằng script an toàn (script từ chối ghi đè cặp khóa đã có):

```powershell
python scripts\generate_rsa_keys.py --create holder
python scripts\generate_rsa_keys.py --create issuer
python scripts\generate_rsa_keys.py --create verifier
```

Mỗi lệnh cần biến password RSA cùng tên role trong `.env`. Script và dashboard kiểm tra public/private pair, dùng PEM SPKI cho public key và fingerprint SHA-256 của DER SPKI. Sau khi `registerKey` thành công, ứng dụng đọc lại public key on-chain để đối chiếu fingerprint; key không thể thay đổi trong MVP.

### 7.6 Sepolia

Điền `SEPOLIA_RPC_URL` và `DEPLOYER_PRIVATE_KEY` vào `.env`, sau đó:

```powershell
$env:SSI_DEPLOYMENT_ID = "sepolia-demo-001"
npm run deploy:sepolia
npm run roles:sepolia
```

Script hiện chỉ deploy/cấp role. Chưa được tuyên bố Sepolia thành công cho tới khi nhóm có contract address và transaction hash thật.

---

## 8. Phân công nhóm

| Vai trò | Phạm vi chính | Thư mục |
|---|---|---|
| **A — Smart Contract** | Contract, role, test contract, deploy Sepolia | `contracts/`, `scripts/` |
| **B — Crypto & IPFS** | AES/RSA, hashing, upload/retrieve Kubo | `crypto/`, `ipfs/` |
| **C — Web3.py & UI** | Contract wrapper và ba dashboard Streamlit | `web3_client/`, `app/` |
| **D — Tests & Docs** | Integration test, test report, WBS và tài liệu nghiệm thu | `test/`, `tests/`, `docs/` |

Chi tiết công việc, tiêu chí hoàn thành và cách phối hợp song song: [`TEAM_HANDOFF.md`](TEAM_HANDOFF.md).

---

## 9. Tài liệu dự án

| Tài liệu | Nội dung |
|---|---|
| [`project-charter.md`](docs/1-initiation-phase/project-charter.md) | Mục tiêu, phạm vi, vai trò và kế hoạch tổng thể |
| [`wbs.xlsx`](docs/1-initiation-phase/wbs.xlsx) | WBS 5 Phase |
| [`architecture.md`](docs/2-planning-phase/architecture.md) | Kiến trúc mới nhất và luồng nghiệp vụ |
| [`contracts-spec.md`](docs/2-planning-phase/contracts-spec.md) | Đặc tả ba smart contract |
| [`interfaces.md`](docs/2-planning-phase/interfaces.md) | ABI, crypto, signature và key policy FROZEN v1 |
| [`key-management.md`](docs/2-planning-phase/key-management.md) | Quy tắc quản lý khóa demo |
| [`test-plan.md`](docs/4-testing-phase/test-plan.md) | Test hiện có và các test còn TODO |

---

## An toàn và giới hạn phạm vi

### Không được commit

- `.env` thật, seed phrase hoặc private key Ethereum.
- RSA private PEM, mật khẩu PEM hoặc keystore.
- Hồ sơ, ảnh cá nhân hoặc bằng cấp thật.
- `node_modules`, môi trường Python, artifact/cache và deployment JSON cục bộ.

### Ngoài phạm vi phiên bản này

- Zero-knowledge proof.
- Multi-chain hoặc bridge.
- DID deactivation độc lập.
- Marketplace, ERC-20 hoặc thanh toán.
- Production key custody và production deployment.

Trước mỗi commit, chạy `git status` và kiểm tra toàn bộ file staged. Chỉ đánh dấu một chức năng hoàn thành khi có code chạy được và bằng chứng kiểm thử tương ứng.

---

<p align="center">
  <b>Blockchain SSI — học tập, kiểm chứng được và không lưu dữ liệu nhạy cảm trực tiếp on-chain.</b>
</p>
