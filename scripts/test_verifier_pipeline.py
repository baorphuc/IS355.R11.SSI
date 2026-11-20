from web3_client.role_keys import verified_pair

import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

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
        raise RuntimeError(f"Missing environment variable: {name}")
    return value.strip()


credential_id = 1

rpc_url = required_env("LOCAL_RPC_URL")
ipfs_url = required_env("IPFS_API_URL")
verifier_address = Web3.to_checksum_address(
    required_env("VERIFIER_ADDRESS")
)
verifier_password = required_env("VERIFIER_RSA_PASSWORD")
registry_address = required_env("SSI_REGISTRY_ADDRESS")



# --------------------------------------------------
# 2. CONNECT BLOCKCHAIN
# --------------------------------------------------

print("\n[1/6] Connecting to blockchain...")

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
verifier_private_pem, verifier_public_pem = verified_pair(registry, verifier_address, ROOT / "keys", "verifier", required_env("VERIFIER_RSA_PASSWORD"))


print("Chain ID:", client.w3.eth.chain_id)
print("Registry:", registry.address)
print("Verifier:", verifier_address)


# --------------------------------------------------
# 3. READ AND VERIFY CREDENTIAL
# --------------------------------------------------

print("\n[2/6] Reading Credential...")

credential = client.get_credential(
    registry,
    credential_id,
)

holder = credential[0]
issuer = credential[1]

portrait_cid = credential[2]
diploma_cid = credential[3]
metadata_cid = credential[4]

doc_hash_onchain = bytes(credential[7])
status = int(credential[9])

if status != 2:
    raise RuntimeError(
        f"Credential is not ISSUED. Current status: {status}"
    )

if not credential[12]:
    raise RuntimeError("Credential SBT has not been minted")

if doc_hash_onchain == bytes(32):
    raise RuntimeError("On-chain docHash is empty")

verification = registry.functions.verifyCredential(
    credential_id
).call()

if not verification[0]:
    raise RuntimeError("Credential verification failed")

print("Credential ID:", credential_id)
print("Holder:", holder)
print("Issuer:", issuer)
print("Status: ISSUED")
print("SBT minted:", credential[12])
print("On-chain docHash:", doc_hash_onchain.hex())
print("verifyCredential: PASS")


# --------------------------------------------------
# 4. CHECK CONSENT AND GET WRAPPED KEY
# --------------------------------------------------

print("\n[3/6] Checking Verifier consent...")

has_access = registry.functions.hasAccess(
    credential_id,
    verifier_address
).call()

active, wrapped_key_for_verifier = (
    registry.functions.getConsent(
        credential_id,
        verifier_address
    ).call()
)

if not has_access or not active:
    raise RuntimeError("Verifier does not have active consent")

wrapped_key_for_verifier = bytes(wrapped_key_for_verifier)

if len(wrapped_key_for_verifier) != 384:
    raise RuntimeError("Invalid Verifier wrapped key length")

print("hasAccess: PASS")
print("Consent active: PASS")
print("Verifier wrapped key:", len(wrapped_key_for_verifier), "bytes")


# --------------------------------------------------
# 5. UNWRAP AES KEY WITH VERIFIER PRIVATE KEY
# --------------------------------------------------

print("\n[4/6] Unwrapping AES key...")

aes_key = unwrap_key(
    wrapped_key_for_verifier,
    verifier_private_pem,
    verifier_password,
)

if len(aes_key) != 32:
    raise RuntimeError("Invalid AES-256 key length")

print("Verifier RSA unwrap: PASS")
print("AES-256 key: PASS")


# --------------------------------------------------
# 6. DOWNLOAD, DECRYPT AND VERIFY FILES
# --------------------------------------------------

print("\n[5/6] Downloading and decrypting from IPFS...")

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
# 7. VERIFY DIPLOMA AGAINST BLOCKCHAIN
# --------------------------------------------------

print("\n[6/6] Verifying diploma integrity...")

recovered_hash = sha256_bytes(
    recovered["diploma"]
)

if recovered_hash != doc_hash_onchain:
    raise RuntimeError(
        "Diploma SHA256 does not match on-chain docHash!"
    )

print("On-chain SHA256:", doc_hash_onchain.hex())
print("Recovered SHA256:", recovered_hash.hex())
print("Diploma integrity: PASS")

print("\n======================================")
print("VERIFIER DECRYPTION PIPELINE: SUCCESS")
print("Credential ID:", credential_id)
print("All 3 files decrypted successfully")
print("Verifier consent: ACTIVE")
print("Diploma integrity: VERIFIED")
print("======================================")
