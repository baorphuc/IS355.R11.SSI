from web3 import Web3
import os

import streamlit as st
from eth_account import Account

from app.common import ROOT, page_header, contract_address
from crypto.crypto_utils import (
    new_aes_key,
    encrypt_bytes,
    wrap_key_for_roles,
    unwrap_key,
    wrap_key,
    sha256_bytes,
)
from ipfs.kubo_client import KuboClient
from web3 import Web3


# ==================================================
# 1. INITIALIZE
# ==================================================

client = page_header("Holder")

holder_private_key = os.getenv("HOLDER_PRIVATE_KEY", "").strip()
registry_address = contract_address("SSI_REGISTRY_ADDRESS")
ipfs_url = os.getenv("IPFS_API_URL", "").strip()

if not holder_private_key:
    st.error("Thiếu HOLDER_PRIVATE_KEY trong .env")
    st.stop()

if not registry_address:
    st.error("Thiếu SSI_REGISTRY_ADDRESS trong .env")
    st.stop()

if not ipfs_url:
    st.error("Thiếu IPFS_API_URL trong .env")
    st.stop()

try:
    holder_address = Account.from_key(holder_private_key).address
except Exception:
    st.error("HOLDER_PRIVATE_KEY không hợp lệ.")
    st.stop()


# ==================================================
# 2. LOAD CONTRACT
# ==================================================

artifact_path = (
    ROOT
    / "artifacts"
    / "contracts"
    / "SSIRegistry.sol"
    / "SSIRegistry.json"
)

try:
    registry = client.load_contract(
        registry_address,
        artifact_path,
    )
except Exception as error:
    st.error(f"Không thể kết nối SSIRegistry: {error}")
    st.stop()


# ==================================================
# 3. HOLDER INFORMATION
# ==================================================

st.subheader("Thông tin Holder")

st.text_input(
    "Địa chỉ ví Holder",
    value=holder_address,
    disabled=True,
)

st.caption("Private key được đọc từ .env, không hiển thị trên giao diện.")


# ==================================================
# 4. CHECK DID
# ==================================================

st.subheader("Đăng ký DID")

try:
    identity = registry.functions.identities(holder_address).call()
    did_exists = identity[0]

    if did_exists:
        st.success("Holder đã đăng ký DID thành công.")
        st.text_input(
            "DID hiện tại",
            value=identity[1],
            disabled=True,
        )

    else:
        did_input = st.text_input(
            "Nhập DID",
            placeholder="did:ssi:local:holder-01",
        )

        if st.button("Tạo DID", type="primary"):
            if not did_input.strip():
                st.warning("Vui lòng nhập DID.")
            else:
                try:
                    with st.spinner("Đang tạo DID..."):
                        result = client.create_did(
                            registry,
                            did_input.strip(),
                            holder_private_key,
                        )

                    st.success("Tạo DID thành công!")
                    st.write("DID:", result["did"])
                    st.code(result["tx_hash"])
                    st.write("Block:", result["block_number"])

                except Exception as error:
                    st.error(f"Tạo DID thất bại: {error}")

except Exception as error:
    st.error(f"Không thể đọc DID: {error}")


# ==================================================
# 5. REQUEST CREDENTIAL
# ==================================================

st.divider()
st.subheader("Tạo yêu cầu Credential")

if not did_exists:
    st.warning("Bạn cần đăng ký DID trước khi gửi yêu cầu Credential.")
    st.stop()

st.write(
    "Chọn đủ ba hồ sơ. Hệ thống sẽ mã hóa từng file "
    "và chỉ upload ciphertext lên IPFS."
)

uploaded_files = st.file_uploader(
    "Chọn hồ sơ",
    type=["jpg", "jpeg", "pdf", "json"],
    accept_multiple_files=True,
    help="Cần 1 ảnh JPG, 1 file PDF và 1 file JSON.",
)

if uploaded_files:
    st.write("Các file đã chọn:")

    for uploaded_file in uploaded_files:
        st.write(
            f"- {uploaded_file.name} "
            f"({uploaded_file.size:,} bytes)"
        )


if st.button("Mã hóa và gửi yêu cầu Credential", type="primary"):

    # ----------------------------------------------
    # Validate uploaded files
    # ----------------------------------------------

    if not uploaded_files:
        st.warning("Vui lòng chọn đủ ba hồ sơ.")
        st.stop()

    file_map = {}

    for uploaded_file in uploaded_files:
        extension = uploaded_file.name.lower().rsplit(".", 1)[-1]

        if extension in ("jpg", "jpeg"):
            category = "portrait"
        elif extension == "pdf":
            category = "diploma"
        elif extension == "json":
            category = "metadata"
        else:
            st.error(f"Định dạng không hỗ trợ: {uploaded_file.name}")
            st.stop()

        if category in file_map:
            st.error(f"Bạn đã chọn nhiều file cho loại {category}.")
            st.stop()

        file_map[category] = uploaded_file.getvalue()

    required_categories = {"portrait", "diploma", "metadata"}

    if set(file_map.keys()) != required_categories:
        st.error("Cần đúng 1 ảnh JPG, 1 PDF và 1 JSON.")
        st.stop()

    if any(not data for data in file_map.values()):
        st.error("Không thể gửi file rỗng.")
        st.stop()

    # ----------------------------------------------
    # Load RSA public keys
    # ----------------------------------------------

    holder_public_path = ROOT / "keys" / "holder_public.pem"
    issuer_public_path = ROOT / "keys" / "issuer_public.pem"

    try:
        holder_public_pem = holder_public_path.read_bytes()
        issuer_public_pem = issuer_public_path.read_bytes()

        # ------------------------------------------
        # Generate AES key and encrypt files
        # ------------------------------------------

        with st.spinner("Đang mã hóa hồ sơ AES-256-GCM..."):

            aes_key = new_aes_key()

            encrypted_files = {}

            for name, plaintext in file_map.items():
                encrypted_files[name] = encrypt_bytes(
                    plaintext,
                    aes_key,
                )

        st.success("Mã hóa ba hồ sơ thành công.")

        # ------------------------------------------
        # Upload encrypted files to IPFS
        # ------------------------------------------

        with st.spinner("Đang upload ciphertext lên IPFS..."):

            kubo = KuboClient(api_url=ipfs_url)

            cids = {}

            for name, encrypted_data in encrypted_files.items():
                cid = kubo.add_bytes(
                    encrypted_data,
                    f"{name}.enc",
                )

                cids[name] = cid

        st.success("Upload IPFS thành công.")

        with st.expander("Thông tin IPFS"):
            for name, cid in cids.items():
                st.write(f"**{name}:**")
                st.code(cid)

        # ------------------------------------------
        # Wrap AES key for Holder and Issuer
        # ------------------------------------------

        with st.spinner("Đang bọc AES key bằng RSA-3072..."):

            wrapped_holder, wrapped_issuer = wrap_key_for_roles(
                aes_key,
                holder_public_pem,
                issuer_public_pem,
            )

        if len(wrapped_holder) != 384 or len(wrapped_issuer) != 384:
            raise ValueError("Wrapped RSA key không đúng 384 bytes.")

        st.success("RSA key wrapping thành công.")

        # ------------------------------------------
        # Request credential on blockchain
        # ------------------------------------------

        with st.spinner("Đang gửi requestCredential lên Blockchain..."):

            result = client.request_credential(
                registry,
                cids["portrait"],
                cids["diploma"],
                cids["metadata"],
                wrapped_holder,
                wrapped_issuer,
                holder_private_key,
            )

        # ------------------------------------------
        # Display transaction result
        # ------------------------------------------

        st.success("Gửi yêu cầu Credential thành công!")

        st.metric(
            "Credential ID",
            result["credential_id"],
        )

        st.write("Holder:", result["holder"])
        st.write("Transaction Hash:")
        st.code(result["tx_hash"])

        st.write("Block Number:", result["block_number"])

        diploma_hash = sha256_bytes(
            file_map["diploma"]
        ).hex()

        st.write("Diploma SHA-256:")
        st.code(diploma_hash)

        st.info(
            "Hồ sơ đã được mã hóa trước khi upload. "
            "AES key không được lưu trực tiếp lên Blockchain."
        )

    except Exception as error:
        st.error(f"Quá trình gửi yêu cầu thất bại: {error}")

        st.warning(
            "Nếu lỗi xảy ra sau khi upload IPFS, một số ciphertext "
            "có thể đã được pin trên Kubo dù transaction chưa thành công."
        )



# ==================================================
# 6. CONSENT MANAGEMENT
# ==================================================

st.divider()
st.subheader("Quản lý Consent")

verifier_address_raw = os.getenv("VERIFIER_ADDRESS", "").strip()
holder_rsa_password = os.getenv("HOLDER_RSA_PASSWORD", "").strip()

if not verifier_address_raw:
    st.error("Thiếu VERIFIER_ADDRESS trong .env")

elif not holder_rsa_password:
    st.error("Thiếu HOLDER_RSA_PASSWORD trong .env")

else:
    verifier_address = Web3.to_checksum_address(
        verifier_address_raw
    )

    st.write("Verifier được cấu hình:")
    st.code(verifier_address)

    consent_id = int(
        st.number_input(
            "Credential ID cần cấp quyền",
            min_value=1,
            value=2,
            step=1,
            key="holder_consent_id",
        )
    )

    try:
        consent_credential = client.get_credential(
            registry,
            consent_id,
        )

        consent_holder = consent_credential[0]
        consent_status = int(consent_credential[9])
        consent_sbt_minted = bool(consent_credential[12])

        if consent_holder.lower() != holder_address.lower():
            st.error("Ví hiện tại không sở hữu Credential này.")

        elif consent_status != 2:
            st.warning("Credential phải ở trạng thái ISSUED.")

        elif not consent_sbt_minted:
            st.warning("Credential chưa được mint SBT.")

        else:
            active, stored_wrapped_key = (
                registry.functions.getConsent(
                    consent_id,
                    verifier_address,
                ).call()
            )

            has_access = registry.functions.hasAccess(
                consent_id,
                verifier_address,
            ).call()

            if active and has_access:
                st.success("Verifier đang có quyền truy cập.")

                if st.button("Revoke Consent", type="secondary"):
                    try:
                        with st.spinner("Đang thu hồi Consent..."):
                            receipt = client.send_transaction(
                                registry.functions.revokeConsent(
                                    consent_id,
                                    verifier_address,
                                ),
                                holder_private_key,
                            )

                        updated_active, _ = (
                            registry.functions.getConsent(
                                consent_id,
                                verifier_address,
                            ).call()
                        )

                        updated_access = registry.functions.hasAccess(
                            consent_id,
                            verifier_address,
                        ).call()

                        if updated_active or updated_access:
                            raise RuntimeError(
                                "Consent vẫn còn hoạt động."
                            )

                        st.success("Đã thu hồi Consent thành công.")
                        st.write("Transaction Hash:")
                        st.code(receipt["transactionHash"].hex())
                        st.write("Block:", receipt["blockNumber"])

                        st.rerun()

                    except Exception as error:
                        st.error(f"Revoke Consent thất bại: {error}")

            else:
                st.info("Verifier hiện chưa có quyền truy cập.")

                if st.button("Grant Consent", type="primary"):
                    try:
                        holder_private_pem = (
                            ROOT / "keys" / "holder_private.pem"
                        ).read_bytes()

                        verifier_public_pem = (
                            ROOT / "keys" / "verifier_public.pem"
                        ).read_bytes()

                        wrapped_holder_key = bytes(
                            consent_credential[5]
                        )

                        if len(wrapped_holder_key) != 384:
                            raise ValueError(
                                "Holder wrapped key không đúng 384 bytes."
                            )

                        with st.spinner("Đang mở AES key bằng RSA..."):
                            aes_key = unwrap_key(
                                wrapped_holder_key,
                                holder_private_pem,
                                holder_rsa_password,
                            )

                        with st.spinner("Đang bọc AES key cho Verifier..."):
                            wrapped_verifier_key = wrap_key(
                                aes_key,
                                verifier_public_pem,
                            )

                        if len(wrapped_verifier_key) != 384:
                            raise ValueError(
                                "Verifier wrapped key không đúng 384 bytes."
                            )

                        with st.spinner("Đang gửi Grant Consent transaction..."):
                            receipt = client.send_transaction(
                                registry.functions.grantConsent(
                                    consent_id,
                                    verifier_address,
                                    wrapped_verifier_key,
                                ),
                                holder_private_key,
                            )

                        updated_active, stored_key = (
                            registry.functions.getConsent(
                                consent_id,
                                verifier_address,
                            ).call()
                        )

                        updated_access = registry.functions.hasAccess(
                            consent_id,
                            verifier_address,
                        ).call()

                        if not updated_active or not updated_access:
                            raise RuntimeError(
                                "Không xác nhận được Consent trên Blockchain."
                            )

                        if bytes(stored_key) != wrapped_verifier_key:
                            raise RuntimeError(
                                "Wrapped key lưu trên Blockchain không khớp."
                            )

                        st.success("Grant Consent thành công!")
                        st.write("Transaction Hash:")
                        st.code(receipt["transactionHash"].hex())
                        st.write("Block:", receipt["blockNumber"])

                        st.rerun()

                    except Exception as error:
                        st.error(f"Grant Consent thất bại: {error}")

    except Exception as error:
        st.error(f"Không thể đọc Consent: {error}")

# ==================================================
# 7. GATED SERVICE
# ==================================================

st.divider()
st.subheader("Truy cập dịch vụ (Gated Service)")

gated_service_address = contract_address("GATED_SERVICE_ADDRESS")

if not gated_service_address:
    st.error("Thiếu GATED_SERVICE_ADDRESS trong .env")

else:
    gated_artifact_path = (
        ROOT
        / "artifacts"
        / "contracts"
        / "GatedService.sol"
        / "GatedService.json"
    )

    try:
        gated_service = client.load_contract(
            gated_service_address,
            gated_artifact_path,
        )

        st.caption(
            "Chỉ Holder đang sở hữu SBT của Credential còn hiệu lực "
            "mới được truy cập dịch vụ."
        )

        service_credential_id = st.number_input(
            "Credential ID cần truy cập",
            min_value=1,
            step=1,
            value=1,
            key="gated_service_credential_id",
        )

        if st.button("Truy cập dịch vụ", type="primary"):
            try:
                with st.spinner("Đang xác minh quyền truy cập..."):
                    result = client.access_service(
                        gated_service,
                        int(service_credential_id),
                        holder_private_key,
                    )

                st.success("Truy cập dịch vụ thành công!")

                st.write("Holder:", result["holder"])
                st.write("Credential ID:", result["credential_id"])
                st.write("Transaction Hash:")
                st.code(result["tx_hash"])
                st.write("Block Number:", result["block_number"])

            except Exception as error:
                st.error(f"Không thể truy cập dịch vụ: {error}")

    except Exception as error:
        st.error(f"Không thể kết nối GatedService: {error}")
