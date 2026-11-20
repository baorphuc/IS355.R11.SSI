
import os
import streamlit as st
from web3 import Web3

from app.common import ROOT, page_header, contract_address, role_key_panel
from crypto.crypto_utils import unwrap_key, decrypt_bytes, sha256_bytes
from ipfs.kubo_client import KuboClient


# ==================================================
# 1. INITIALIZE
# ==================================================

client = page_header("Verifier")

if not client.w3.is_connected():
    st.stop()

if client.w3.eth.chain_id != 31337:
    st.error("Dashboard hiện chỉ hỗ trợ Hardhat local chain 31337.")
    st.stop()


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        st.error(f"Thiếu biến môi trường {name} trong .env")
        st.stop()
    return value


verifier_address = Web3.to_checksum_address(
    required_env("VERIFIER_ADDRESS")
)
verifier_password = required_env("VERIFIER_RSA_PASSWORD")
ipfs_url = required_env("IPFS_API_URL")

registry_address = Web3.to_checksum_address(
    contract_address("SSI_REGISTRY_ADDRESS")
)


# ==================================================
# 2. LOAD CONTRACT AND IPFS
# ==================================================

registry_artifact = (
    ROOT / "artifacts" / "contracts"
    / "SSIRegistry.sol" / "SSIRegistry.json"
)

try:
    registry = client.load_contract(
        registry_address,
        registry_artifact,
    )
    ipfs = KuboClient(ipfs_url)

except Exception as error:
    st.error(f"Không thể khởi tạo Registry/IPFS: {error}")
    st.stop()


verifier_private_pem, verifier_public_pem = role_key_panel(client, registry, "verifier", verifier_address)

# ==================================================
# 3. VERIFIER INFORMATION
# ==================================================

st.subheader("Thông tin Verifier")

st.text_input(
    "Địa chỉ ví Verifier",
    value=verifier_address,
    disabled=True,
)

st.caption(
    "RSA private key được đọc từ keys/verifier_private.pem. "
    "Không hiển thị private key trên giao diện."
)


# ==================================================
# 4. CREDENTIAL SELECTION
# ==================================================

st.divider()
st.subheader("Xác minh Credential")

credential_id = int(
    st.number_input(
        "Credential ID",
        min_value=1,
        value=2,
        step=1,
        key="verifier_credential_id",
    )
)

credential = None

try:
    credential = client.get_credential(registry, credential_id)
except Exception as error:
    st.error(f"Không đọc được Credential: {error}")


# ==================================================
# 5. PUBLIC VERIFICATION
# ==================================================

if credential is not None:
    holder = credential[0]
    issuer = credential[1]
    portrait_cid = credential[2]
    diploma_cid = credential[3]
    metadata_cid = credential[4]
    doc_hash = bytes(credential[7])
    status = int(credential[9])
    issued_at = int(credential[10])
    revoked_at = int(credential[11])
    sbt_minted = bool(credential[12])

    status_labels = {
        0: "NONE",
        1: "REQUESTED",
        2: "ISSUED",
        3: "REVOKED",
    }

    st.markdown("### Thông tin Credential")

    st.write(f"**Credential ID:** {credential_id}")
    st.write(f"**Holder:** `{holder}`")
    st.write(f"**Issuer:** `{issuer}`")
    st.write(
        f"**Trạng thái:** {status_labels.get(status, 'UNKNOWN')}"
    )
    st.write(f"**SBT đã mint:** {'Có' if sbt_minted else 'Chưa'}")

    st.markdown("**Thông tin IPFS**")

    with st.expander("Xem ba CID"):
        st.write("Portrait CID")
        st.code(portrait_cid)

        st.write("Diploma CID")
        st.code(diploma_cid)

        st.write("Metadata CID")
        st.code(metadata_cid)

    st.write("**Diploma docHash (SHA-256)**")
    st.code(Web3.to_hex(doc_hash))

    if st.button("Verify Credential", type="primary"):
        try:
            verification = client.verify_credential(
            registry, credential_id
        )
            is_valid = bool(verification[0])

            if is_valid and status == 2:
                st.success(
                    "Credential hợp lệ trên Blockchain."
                )
            elif status == 3:
                st.error("Credential đã bị thu hồi.")
            else:
                st.warning(
                    "Credential chưa được phát hành "
                    "hoặc không hợp lệ."
                )

        except Exception as error:
            st.error(f"Lỗi xác minh: {error}")


# ==================================================
# 6. CONSENT AND ACCESS CHECK
# ==================================================

st.divider()
st.subheader("Kiểm tra quyền truy cập")

if credential is not None:
    try:
        consent_active, wrapped_verifier_key = client.get_consent(
            registry,
            credential_id,
            verifier_address,
        )

        has_access = client.has_access(
            registry,
            credential_id,
            verifier_address,
        )

        if consent_active and has_access:
            st.success("Verifier đang được Holder cấp quyền.")
        else:
            st.warning(
                "Verifier chưa có quyền truy cập. "
                "Holder cần Grant Consent trước."
            )

    except Exception as error:
        st.error(f"Không kiểm tra được Consent: {error}")


# ==================================================
# 7. DECRYPT AND VERIFY DOCUMENTS
# ==================================================

st.divider()
st.subheader("Giải mã và xác minh hồ sơ")

st.caption(
    "Chỉ giải mã khi Credential còn ISSUED, SBT đã mint "
    "và Consent của Verifier đang hoạt động."
)

if credential is not None:
    if st.button("Giải mã và xác minh hồ sơ", type="primary"):

        try:
            # 1. Kiểm tra trạng thái Credential
            if status != 2:
                raise ValueError(
                    "Credential không ở trạng thái ISSUED."
                )

            if not sbt_minted:
                raise ValueError(
                    "Credential chưa được mint SBT."
                )

            # 2. Kiểm tra Consent và quyền truy cập
            consent_active, wrapped_verifier_key = (
                client.get_consent(
                    registry,
                    credential_id,
                    verifier_address,
                )
            )

            has_access = client.has_access(
                registry,
                credential_id,
                verifier_address,
            )

            if not consent_active or not has_access:
                raise PermissionError(
                    "Holder chưa cấp Consent hoặc Consent đã bị thu hồi."
                )

            if not wrapped_verifier_key:
                raise ValueError(
                    "Không tìm thấy RSA wrapped key dành cho Verifier."
                )

            # 3. Đọc RSA private key của Verifier
            # 4. RSA unwrap AES key
            aes_key = unwrap_key(
                bytes(wrapped_verifier_key),
                verifier_private_pem,
                verifier_password,
            )

            if len(aes_key) != 32:
                raise ValueError("AES key không hợp lệ.")

            st.success("RSA unwrap AES key thành công.")

            # 5. Download ciphertext từ IPFS
            encrypted_files = {
                "portrait": portrait_cid,
                "diploma": diploma_cid,
                "metadata": metadata_cid,
            }

            decrypted_files = {}

            for filename, cid in encrypted_files.items():
                encrypted_data = ipfs.cat(cid)

                plaintext = decrypt_bytes(
                    encrypted_data,
                    aes_key,
                )

                decrypted_files[filename] = plaintext

            st.success(
                "Đã tải và giải mã thành công cả ba hồ sơ từ IPFS."
            )

            # 6. Tính SHA-256 của ba hồ sơ
            st.markdown("### Kết quả giải mã")

            for filename, plaintext in decrypted_files.items():
                digest = sha256_bytes(plaintext)

                st.write(
                    f"**{filename}:** {len(plaintext):,} bytes"
                )
                st.caption(
                    f"SHA-256: {digest.hex()}"
                )

            # 7. Đối chiếu diploma hash với Blockchain
            diploma_hash = sha256_bytes(
                decrypted_files["diploma"]
            )

            st.markdown("### Xác minh bằng tốt nghiệp")

            st.write("SHA-256 tính từ PDF:")
            st.code(diploma_hash.hex())

            st.write("docHash lưu trên Blockchain:")
            st.code(doc_hash.hex())

            if diploma_hash == doc_hash:
                st.success(
                    "XÁC MINH THÀNH CÔNG: "
                    "Hash bằng tốt nghiệp trùng khớp Blockchain."
                )
            else:
                st.error(
                    "XÁC MINH THẤT BẠI: "
                    "Hash bằng tốt nghiệp không khớp Blockchain."
                )

        except PermissionError as error:
            st.error(str(error))

        except Exception as error:
            st.error(
                f"Giải mã hoặc xác minh thất bại: {error}"
            )
