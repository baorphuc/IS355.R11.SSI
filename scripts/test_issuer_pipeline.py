
import os
from pathlib import Path

from dotenv import load_dotenv

from crypto.crypto_utils import (
    unwrap_key,
    decrypt_bytes,
    sha256_bytes,
)
from ipfs.kubo_client import KuboClient
from web3_client.client import SSIClient


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def required_env(name):
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"Thiếu biến môi trường: {name}")
    return value.strip()


credential_id = 1

rpc_url = required_env("LOCAL_RPC_URL")
ipfs_url = required_env("IPFS_API_URL")
issuer_password = required_env("ISSUER_RSA_PASSWORD")
registry_address = required_env("SSI_REGISTRY_ADDRESS")

issuer_private_pem = (
    ROOT / "keys" / "issuer_private.pem"
).read_bytes()


# --------------------------------------------------
# 2. CONNECT BLOCKCHAIN
# --------------------------------------------------

print("\n[1/5] Connecting to blockchain...")

client = SSIClient(
    rpc_url=rpc_url,
    expected_chain_id=31337,
)

client.require_connection()

artifact = (
    ROOT
    / "artifacts"
    / "contracts"
    / "SSIRegistry.sol"
    / "SSIRegistry.json"
)

registry = client.load_contract(
    registry_address,
    artifact,
)

print("Chain ID:", client.w3.eth.chain_id)
print("Registry:", registry.address)


# --------------------------------------------------
# 3. READ CREDENTIAL
# --------------------------------------------------

print("\n[2/5] Reading Credential...")

credential = client.get_credential(
    registry,
    credential_id,
)

holder = credential[0]
issuer = credential[1]

portrait_cid = credential[2]
diploma_cid = credential[3]
metadata_cid = credential[4]

wrapped_key_for_issuer = bytes(credential[6])

doc_hash_onchain = bytes(credential[7])
status = int(credential[9])

if int(credential[9]) != 1:
    raise RuntimeError(
        f"Credential không ở trạng thái REQUESTED: {status}"
    )

if issuer.lower() != "0x0000000000000000000000000000000000000000":
    raise RuntimeError(
        "Credential đã có Issuer, không còn ở trạng thái yêu cầu ban đầu"
    )

if not wrapped_key_for_issuer:
    raise RuntimeError("Không tìm thấy wrapped key dành cho Issuer")

print("Credential ID:", credential_id)
print("Holder:", holder)
print("Issuer:", issuer)
print("Status:", status)
print("Portrait CID:", portrait_cid)
print("Diploma CID:", diploma_cid)
print("Metadata CID:", metadata_cid)
print("Issuer wrapped key:", len(wrapped_key_for_issuer), "bytes")


# --------------------------------------------------
# 4. UNWRAP AES KEY
# --------------------------------------------------

print("\n[3/5] Unwrapping AES key...")

aes_key = unwrap_key(
    wrapped_key_for_issuer,
    issuer_private_pem,
    issuer_password,
)

if len(aes_key) != 32:
    raise RuntimeError("AES key không đúng 32 bytes")

print("Issuer RSA unwrap: PASS")
print("AES-256 key: PASS")


# --------------------------------------------------
# 5. DOWNLOAD AND DECRYPT FILES
# --------------------------------------------------

print("\n[4/5] Downloading and decrypting from IPFS...")

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

    print(f"{name}: PASS")
    print("  Ciphertext bytes:", len(encrypted))
    print("  Plaintext bytes:", len(plaintext))
    print("  SHA256:", sha256_bytes(plaintext).hex())


# --------------------------------------------------
# 6. VERIFY DIPLOMA
# --------------------------------------------------

print("\n[5/5] Verifying diploma integrity...")

fixture_diploma = (
    ROOT
    / "tests"
    / "fixtures"
    / "crypto_ipfs_v1"
    / "diploma.pdf"
)

expected_hash = sha256_bytes(
    fixture_diploma.read_bytes()
)

recovered_hash = sha256_bytes(
    recovered["diploma"]
)

if recovered_hash != expected_hash:
    raise RuntimeError("Diploma SHA256 mismatch!")

print("Expected SHA256:", expected_hash.hex())
print("Recovered SHA256:", recovered_hash.hex())
print("Diploma integrity: PASS")

# Credential mới được yêu cầu nên chưa có docHash on-chain.
if doc_hash_onchain == bytes(32):
    print("On-chain docHash: not issued yet (expected)")
elif doc_hash_onchain != recovered_hash:
    raise RuntimeError("On-chain docHash mismatch!")

print("\n======================================")
print("ISSUER DECRYPTION PIPELINE: PASS")
print("Credential ID:", credential_id)
print("All 3 files decrypted successfully")
print("======================================")
