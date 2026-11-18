
import os
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

from crypto.crypto_utils import (
    new_aes_key,
    encrypt_bytes,
    wrap_key_for_roles,
    sha256_bytes,
)
from ipfs.kubo_client import KuboClient
from web3_client.client import SSIClient


# --------------------------------------------------
# 1. LOAD CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def required_env(name):
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"Thiếu biến môi trường: {name}")
    return value.strip()


rpc_url = required_env("LOCAL_RPC_URL")
ipfs_url = required_env("IPFS_API_URL")
holder_private_key = required_env("HOLDER_PRIVATE_KEY")
issuer_address = Web3.to_checksum_address(
    required_env("ISSUER_ADDRESS")
)
registry_address = required_env("SSI_REGISTRY_ADDRESS")


# --------------------------------------------------
# 2. CONNECT BLOCKCHAIN
# --------------------------------------------------

print("\n[1/7] Connecting to local blockchain...")

client = SSIClient(
    rpc_url=rpc_url,
    expected_chain_id=31337,
)

client.require_connection()

holder_address = Account.from_key(
    holder_private_key
).address

print("Chain ID:", client.w3.eth.chain_id)
print("Holder:", holder_address)
print("Issuer:", issuer_address)

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

print("SSIRegistry connected:", registry.address)


# --------------------------------------------------
# 3. CHECK OR CREATE HOLDER DID
# --------------------------------------------------

print("\n[2/7] Checking Holder DID...")

identity = registry.functions.identities(
    holder_address
).call()

if identity[0]:
    print("Holder already has DID:", identity[1])
else:
    did = "did:ssi:local:holder-01"

    result = client.create_did(
        registry,
        did,
        holder_private_key,
    )

    print("DID created:", result["did"])
    print("DID transaction:", result["tx_hash"])


# --------------------------------------------------
# 4. LOAD FIXTURES AND ENCRYPT
# --------------------------------------------------

print("\n[3/7] Encrypting credential files...")

fixture_dir = ROOT / "tests" / "fixtures" / "crypto_ipfs_v1"

files = {
    "portrait": fixture_dir / "portrait.jpg",
    "diploma": fixture_dir / "diploma.pdf",
    "metadata": fixture_dir / "metadata.json",
}

for path in files.values():
    if not path.is_file():
        raise FileNotFoundError(path)

aes_key = new_aes_key()

encrypted_files = {}

for name, path in files.items():
    plaintext = path.read_bytes()
    encrypted = encrypt_bytes(plaintext, aes_key)

    encrypted_files[name] = encrypted

    print(f"{name}: encrypted")
    print("  Plaintext SHA256:", sha256_bytes(plaintext).hex())
    print("  Encrypted bytes:", len(encrypted))

diploma_hash = sha256_bytes(
    files["diploma"].read_bytes()
)


# --------------------------------------------------
# 5. UPLOAD ENCRYPTED FILES TO IPFS
# --------------------------------------------------

print("\n[4/7] Uploading encrypted files to IPFS...")

kubo = KuboClient(api_url=ipfs_url)

cids = {}

for name, encrypted in encrypted_files.items():
    cid = kubo.add_bytes(
        encrypted,
        f"{name}.enc",
    )

    cids[name] = cid
    print(f"{name} CID:", cid)


# --------------------------------------------------
# 6. WRAP AES KEY FOR HOLDER AND ISSUER
# --------------------------------------------------

print("\n[5/7] Wrapping AES key with RSA-3072...")

holder_public_pem = (
    ROOT / "keys" / "holder_public.pem"
).read_bytes()

issuer_public_pem = (
    ROOT / "keys" / "issuer_public.pem"
).read_bytes()

wrapped_holder, wrapped_issuer = wrap_key_for_roles(
    aes_key,
    holder_public_pem,
    issuer_public_pem,
)

if len(wrapped_holder) != 384 or len(wrapped_issuer) != 384:
    raise RuntimeError("Wrapped key không đúng 384 bytes")

print("Holder wrapped key: 384 bytes")
print("Issuer wrapped key: 384 bytes")


# --------------------------------------------------
# 7. REQUEST CREDENTIAL ON-CHAIN
# --------------------------------------------------

print("\n[6/7] Requesting credential...")

result = client.request_credential(
    registry,
    cids["portrait"],
    cids["diploma"],
    cids["metadata"],
    wrapped_holder,
    wrapped_issuer,
    holder_private_key,
)

credential_id = result["credential_id"]

print("Credential ID:", credential_id)
print("Transaction:", result["tx_hash"])
print("Block:", result["block_number"])


# --------------------------------------------------
# 8. READ BACK CREDENTIAL
# --------------------------------------------------

print("\n[7/7] Reading credential from blockchain...")

credential = client.get_credential(
    registry,
    credential_id,
)

print("Credential data:", credential)

print("\nDiploma SHA256 (for later Issuer issuance):")
print(diploma_hash.hex())

print("\n======================================")
print("HOLDER PIPELINE COMPLETED SUCCESSFULLY")
print("Credential ID:", credential_id)
print("======================================")
