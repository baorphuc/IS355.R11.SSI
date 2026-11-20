
import os

import streamlit as st
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from app.common import ROOT, page_header, contract_address, role_key_panel
from crypto.crypto_utils import (
    unwrap_key,
    decrypt_bytes,
    sha256_bytes,
)
from ipfs.kubo_client import KuboClient


# ==================================================
# 1. INITIALIZE
# ==================================================

client = page_header("Issuer")

if client.w3.eth.chain_id != 31337:
    st.error("Dashboard hiện chỉ hỗ trợ Hardhat local chain 31337.")
    st.stop()

def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        st.error(f"Thiếu biến môi trường {name} trong .env")
        st.stop()
    return value


issuer_private_key = required_env("ISSUER_PRIVATE_KEY")
issuer_address = Web3.to_checksum_address(
    required_env("ISSUER_ADDRESS")
)
registry_address = Web3.to_checksum_address(
    contract_address("SSI_REGISTRY_ADDRESS")
)
ipfs_url = required_env("IPFS_API_URL")
issuer_password = required_env("ISSUER_RSA_PASSWORD")

actual_issuer = Account.from_key(issuer_private_key).address

if actual_issuer.lower() != issuer_address.lower():
    st.error("ISSUER_PRIVATE_KEY không khớp ISSUER_ADDRESS.")
    st.stop()


# ==================================================
# 2. LOAD CONTRACTS
# ==================================================

registry_artifact = (
    ROOT
    / "artifacts"
    / "contracts"
    / "SSIRegistry.sol"
    / "SSIRegistry.json"
)

sbt_artifact = (
    ROOT
    / "artifacts"
    / "contracts"
    / "IdentitySBT.sol"
    / "IdentitySBT.json"
)

try:
    registry = client.load_contract(
        registry_address,
        registry_artifact,
    )

    sbt_address = contract_address("IDENTITY_SBT_ADDRESS")

    if not sbt_address:
        raise ValueError("Thiếu IDENTITY_SBT_ADDRESS trong .env")

    sbt = client.load_contract(
        sbt_address,
        sbt_artifact,
    )

except Exception as error:
    st.error(f"Không thể tải Smart Contract: {error}")
    st.stop()


issuer_private_pem, issuer_public_pem = role_key_panel(client, registry, "issuer", issuer_address)

# ==================================================
# 3. CHECK ISSUER ROLE
# ==================================================

st.subheader("Thông tin Issuer")

st.text_input(
    "Địa chỉ ví Issuer",
    value=issuer_address,
    disabled=True,
)

issuer_role = registry.functions.ISSUER_ROLE().call()

has_role = registry.functions.hasRole(
    issuer_role,
    issuer_address,
).call()

if not has_role:
    st.error("Ví Issuer chưa được cấp ISSUER_ROLE.")
    st.stop()

st.success("Issuer có quyền phát hành Credential.")


# ==================================================
# 4. SELECT CREDENTIAL
# ==================================================

st.divider()
st.subheader("Xử lý yêu cầu Credential")

credential_id = int(
    st.number_input(
        "Credential ID",
        min_value=1,
        value=2,
        step=1,
    )
)

# Không sử dụng kết quả xác minh cũ khi đổi Credential ID.
if st.session_state.get("issuer_verified_id") != credential_id:
    st.session_state.pop("issuer_verified_id", None)
    st.session_state.pop("issuer_verified_hash", None)

try:
    credential = client.get_credential(
        registry,
        credential_id,
    )

except Exception as error:
    st.error(f"Không đọc được Credential: {error}")
    st.stop()


# Solidity enum:
# NONE=0, REQUESTED=1, ISSUED=2, REVOKED=3

status = int(credential[9])

status_labels = {
    0: "NONE",
    1: "REQUESTED",
    2: "ISSUED",
    3: "REVOKED",
}

holder = credential[0]
current_issuer = credential[1]

portrait_cid = credential[2]
diploma_cid = credential[3]
metadata_cid = credential[4]

wrapped_key_for_issuer = bytes(credential[6])
doc_hash_onchain = bytes(credential[7])

sbt_minted = bool(credential[12])

st.markdown("### Thông tin Credential")

st.write("**Credential ID:**", credential_id)
st.write("**Holder:**", holder)
st.write("**Issuer hiện tại:**", current_issuer)
st.write("**Trạng thái:**", status_labels.get(status, "UNKNOWN"))

with st.expander("Thông tin IPFS"):
    st.write("Portrait CID:")
    st.code(portrait_cid)

    st.write("Diploma CID:")
    st.code(diploma_cid)

    st.write("Metadata CID:")
    st.code(metadata_cid)


# ==================================================
# 5. DECRYPT AND VERIFY DOCUMENTS
# ==================================================

st.divider()
st.subheader("Giải mã và xác minh hồ sơ")

st.write(
    "Issuer sử dụng RSA private key để mở AES key, "
    "sau đó tải và giải mã ba hồ sơ từ IPFS."
)

if status == 1:

    if st.button(
        "Giải mã và xác minh hồ sơ",
        type="primary",
    ):

        try:
            if not wrapped_key_for_issuer:
                raise ValueError("Không tìm thấy wrapped key của Issuer.")

            if len(wrapped_key_for_issuer) != 384:
                raise ValueError("Wrapped key không đúng 384 bytes.")

            with st.spinner("Đang giải mã RSA-3072..."):

                aes_key = unwrap_key(
                    wrapped_key_for_issuer,
                    issuer_private_pem,
                    issuer_password,
                )

            if len(aes_key) != 32:
                raise ValueError("AES key không đúng 32 bytes.")

            st.success("RSA unwrap thành công.")

            with st.spinner("Đang tải và giải mã hồ sơ từ IPFS..."):

                kubo = KuboClient(api_url=ipfs_url)

                cids = {
                    "portrait": portrait_cid,
                    "diploma": diploma_cid,
                    "metadata": metadata_cid,
                }

                recovered = {}

                for name, cid in cids.items():

                    encrypted = kubo.cat(cid)

                    plaintext = decrypt_bytes(
                        encrypted,
                        aes_key,
                    )

                    recovered[name] = plaintext

            st.success("Đã giải mã thành công cả ba hồ sơ.")

            st.markdown("### Kết quả giải mã")

            for name, plaintext in recovered.items():

                st.write(
                    f"**{name}:** "
                    f"{len(plaintext):,} bytes"
                )

                st.caption(
                    f"SHA-256: {sha256_bytes(plaintext).hex()}"
                )

            # Tính hash từ PDF vừa giải mã từ IPFS.
            diploma_hash = sha256_bytes(
                recovered["diploma"]
            )

            st.markdown("### Xác minh bằng tốt nghiệp")

            st.write("Diploma SHA-256:")
            st.code(diploma_hash.hex())

            # Credential REQUESTED chưa có docHash on-chain.
            if doc_hash_onchain != bytes(32):
                raise ValueError(
                    "Credential REQUESTED nhưng docHash on-chain "
                    "không bằng zero."
                )

            # Lưu kết quả xác minh trong Streamlit session.
            st.session_state["issuer_verified_id"] = credential_id
            st.session_state["issuer_verified_hash"] = diploma_hash

            st.success(
                "Xác minh hồ sơ thành công. "
                "Có thể tiến hành phát hành Credential."
            )

        except Exception as error:
            st.session_state.pop("issuer_verified_id", None)
            st.session_state.pop("issuer_verified_hash", None)

            st.error(f"Giải mã hoặc xác minh thất bại: {error}")

else:
    st.info(
        "Chỉ Credential ở trạng thái REQUESTED "
        "mới có thể thực hiện bước giải mã và xác minh ban đầu."
    )


# ==================================================
# 6. ISSUE CREDENTIAL
# ==================================================

st.divider()
st.subheader("Phát hành Credential")

verified_id = st.session_state.get("issuer_verified_id")
verified_hash = st.session_state.get("issuer_verified_hash")

if (
    status == 1
    and verified_id == credential_id
    and isinstance(verified_hash, bytes)
):

    st.success("Hồ sơ đã được xác minh.")

    if st.button("Ký và phát hành Credential", type="primary"):

        try:
            with st.spinner("Đang ký EIP-191..."):

                contract_digest = registry.functions.signingDigest(
                    credential_id,
                    verified_hash,
                ).call()

                message = encode_defunct(
                    primitive=contract_digest,
                )

                signed_message = Account.sign_message(
                    message,
                    private_key=issuer_private_key,
                )

                signature = bytes(signed_message.signature)

                recovered_signer = Account.recover_message(
                    message,
                    signature=signature,
                )

                if recovered_signer.lower() != issuer_address.lower():
                    raise ValueError(
                        "Chữ ký EIP-191 không khớp địa chỉ Issuer."
                    )

            with st.spinner("Đang gửi issueCredential transaction..."):

                receipt = client.send_transaction(
                    registry.functions.issueCredential(
                        credential_id,
                        verified_hash,
                        signature,
                    ),
                    issuer_private_key,
                )

            updated = client.get_credential(
                registry,
                credential_id,
            )

            verification = client.verify_credential(
                registry,
                credential_id,
            )

            if int(updated[9]) != 2:
                raise RuntimeError("Credential chưa chuyển sang ISSUED.")

            if bytes(updated[7]) != verified_hash:
                raise RuntimeError("On-chain docHash không khớp.")

            if not verification[0]:
                raise RuntimeError("verifyCredential trả về false.")

            st.success("Phát hành Credential thành công!")

            st.write("Transaction Hash:")
            st.code(receipt["transactionHash"].hex())

            st.write("Block Number:", receipt["blockNumber"])
            st.write("Status: ISSUED")

            st.session_state.pop("issuer_verified_id", None)
            st.session_state.pop("issuer_verified_hash", None)

            st.rerun()

        except Exception as error:
            st.error(f"Phát hành Credential thất bại: {error}")

elif status == 1:
    st.info("Hãy giải mã và xác minh hồ sơ trước khi phát hành.")

elif status == 2:
    st.success("Credential đã được phát hành.")

elif status == 3:
    st.error("Credential đã bị thu hồi. Không thể phát hành lại.")


# ==================================================
# 7. MINT SBT
# ==================================================

st.divider()
st.subheader("Mint Soulbound Token")

# Đọc lại trạng thái sau khi Issue.
try:
    current_credential = client.get_credential(
        registry,
        credential_id,
    )

    current_status = int(current_credential[9])
    current_minted = bool(current_credential[12])
    current_holder = Web3.to_checksum_address(
        current_credential[0]
    )

except Exception as error:
    st.error(f"Không đọc được trạng thái SBT: {error}")
    st.stop()


if current_status == 2:

    st.divider()
    st.subheader("Thu hồi Credential")

    st.warning(
        "Cảnh báo: Thu hồi Credential là thao tác không thể hoàn tác. "
        "Nếu đã mint SBT, SBT sẽ tự động bị burn."
    )

    confirm_revoke = st.checkbox(
        "Tôi xác nhận muốn thu hồi Credential này",
        key=f"confirm_revoke_{credential_id}",
    )

    if st.button(
        "Revoke Credential",
        type="secondary",
        disabled=not confirm_revoke,
        key=f"revoke_credential_{credential_id}",
    ):
        try:
            with st.spinner("Đang thu hồi Credential trên Blockchain..."):
                result = client.revoke_credential(
                    registry,
                    credential_id,
                    issuer_private_key,
                )

            updated = client.get_credential(
                registry,
                credential_id,
            )

            if int(updated[9]) != 3:
                raise RuntimeError(
                    "Giao dịch hoàn tất nhưng trạng thái chưa chuyển thành REVOKED."
                )

            if bool(updated[12]):
                raise RuntimeError(
                    "Credential đã REVOKED nhưng sbtMinted vẫn còn True."
                )

            st.success("Thu hồi Credential thành công!")

            st.write("Transaction Hash:")
            st.code(result["tx_hash"])

            st.write("Block Number:", result["block_number"])
            st.write("Credential ID:", result["credential_id"])

            st.rerun()

        except Exception as error:
            st.error(f"Thu hồi Credential thất bại: {error}")

    if current_minted:

        st.success("Credential đã được mint SBT.")

        try:
            owner = sbt.functions.ownerOf(
                credential_id
            ).call()

            st.write("SBT Owner:", owner)

        except Exception as error:
            st.warning(f"Không đọc được SBT owner: {error}")

    else:

        st.info(
            "Credential đã ISSUED nhưng chưa được mint SBT."
        )

        if st.button("Mint SBT cho Holder", type="primary"):

            try:
                with st.spinner("Đang mint SBT..."):

                    receipt = client.send_transaction(
                        registry.functions.mintSBT(
                            credential_id
                        ),
                        issuer_private_key,
                    )

                updated = client.get_credential(
                    registry,
                    credential_id,
                )

                balance = sbt.functions.balanceOf(
                    current_holder
                ).call()

                owner = sbt.functions.ownerOf(
                    credential_id
                ).call()

                if not updated[12]:
                    raise RuntimeError("sbtMinted chưa được cập nhật.")

                if owner.lower() != current_holder.lower():
                    raise RuntimeError("SBT owner không khớp Holder.")

                st.success("Mint SBT thành công!")

                st.write("Transaction Hash:")
                st.code(receipt["transactionHash"].hex())

                st.write("Block Number:", receipt["blockNumber"])
                st.write("Holder SBT balance:", balance)
                st.write("SBT Owner:", owner)

                st.rerun()

            except Exception as error:
                st.error(f"Mint SBT thất bại: {error}")

elif current_status == 3:
    st.warning("Credential đã REVOKED, không thể mint SBT.")

else:
    st.info("Cần phát hành Credential trước khi mint SBT.")
