import streamlit as st
from app.common import page_header

page_header("Holder")
st.subheader("Tạo DID và yêu cầu credential")
st.text_input("DID mô phỏng", placeholder="did:ssi:0x...")
st.file_uploader("Hồ sơ giả", accept_multiple_files=True, type=["jpg", "pdf", "json"])
st.info("Scaffold UI: crypto/IPFS đã có module riêng; nối giao dịch createDID/requestCredential là TODO(C).")
st.button("Gửi yêu cầu", disabled=True, help="TODO(C): nối ABI và ví testnet cục bộ")

st.subheader("Consent")
st.text_input("Credential ID", key="consent_id")
st.text_input("Địa chỉ Verifier")
st.button("Grant consent", disabled=True)
st.button("Revoke consent", disabled=True)
