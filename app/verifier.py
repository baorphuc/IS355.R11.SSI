import streamlit as st
from app.common import page_header

page_header("Verifier")
st.subheader("Xác minh công khai")
credential_id = st.number_input("Credential ID", min_value=1, step=1)
st.info("Scaffold UI: verifyCredential/hasAccess sẽ dùng web3_client. Không cần consent để xem trạng thái công khai.")
st.button("Verify", disabled=True)

st.subheader("Token-gated access")
st.caption("accessService(uint256 credentialId) là giao dịch và phát event ServiceAccessed.")
st.button("Access service", disabled=True)
