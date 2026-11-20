
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from web3_client.client import SSIClient


ROOT = Path(__file__).resolve().parents[1]

# Load environment variables from project root.
load_dotenv(ROOT / ".env")


def page_header(role: str) -> SSIClient:
    st.set_page_config(
        page_title=f"SSI MVP - {role}",
        page_icon="🔐",
    )

    st.title(f"SSI MVP — {role}")
    st.caption("Prototype học tập. Chỉ dùng dữ liệu giả và ví testnet.")

    client = SSIClient()

    try:
        client.require_connection()
        st.success(
            f"RPC đã kết nối · chainId {client.w3.eth.chain_id}"
        )
    except ConnectionError as error:
        st.error(str(error))

    return client


def contract_address(name: str) -> str:
    return os.getenv(name, "").strip()


def role_key_panel(client, registry, role, wallet):
    from crypto.role_keys import fingerprint, load_pair
    from web3_client.role_keys import registered, register_pair, verify_public

    directory = ROOT / "keys"
    password = os.getenv(role.upper() + "_RSA_PASSWORD", "")
    try:
        secret, pem = load_pair(directory, role, password)
        digest = fingerprint(pem)
        st.caption(f"{role} · {wallet} · RSA SHA-256: {digest}")
        if not registered(registry, wallet):
            confirmed = st.checkbox("Tôi đã sao lưu PEM mã hóa và kiểm tra fingerprint.",
                                    key=f"backup-{wallet}-{digest}")
            if not st.button("Đăng ký khóa RSA một lần", disabled=not confirmed):
                st.info("Cần đăng ký khóa trước khi xử lý hồ sơ.")
                st.stop()
            register_pair(client, registry, wallet, os.getenv(role.upper() + "_PRIVATE_KEY"),
                          directory, role, password, expected_fingerprint=digest)
        verify_public(registry, wallet, pem)
        return secret, pem
    except (FileNotFoundError, PermissionError, ValueError) as error:
        st.error(f"RSA: {type(error).__name__}. Kiểm tra cặp PEM, quyền đọc, ví và fingerprint đã đăng ký.")
    except Exception:
        st.error("Không thể xác minh đăng ký RSA. Kiểm tra kết nối và giao dịch.")
    st.stop()
