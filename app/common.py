import os
from pathlib import Path
import streamlit as st

from web3_client.client import SSIClient


ROOT = Path(__file__).resolve().parents[1]


def page_header(role: str) -> SSIClient:
    st.set_page_config(page_title=f"SSI MVP - {role}", page_icon="🔐")
    st.title(f"SSI MVP — {role}")
    st.caption("Prototype học tập. Chỉ dùng dữ liệu giả và ví testnet.")
    client = SSIClient()
    try:
        client.require_connection()
        st.success(f"RPC đã kết nối · chainId {client.w3.eth.chain_id}")
    except ConnectionError as error:
        st.error(str(error))
    return client


def contract_address(name: str) -> str:
    return os.getenv(name, "")
