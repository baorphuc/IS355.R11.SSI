import streamlit as st
from app.common import page_header

page_header("Issuer")
st.subheader("Phát hành / thu hồi")
credential_id = st.number_input("Credential ID", min_value=1, step=1)
st.code(f"credentialId={credential_id}")
st.info("Scaffold UI: ký EIP-191, issue, mint và revoke là TODO(C) sau khi nhóm chốt cách nhập khóa demo.")
st.button("Issue credential", disabled=True)
st.button("Mint SBT", disabled=True)
st.button("Revoke credential", disabled=True)
