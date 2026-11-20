from web3_client.role_keys import verified_pair

import os
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from crypto.crypto_utils import sha256_bytes
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
issuer_private_key = required_env("ISSUER_PRIVATE_KEY")
issuer_address = Web3.to_checksum_address(
    required_env("ISSUER_ADDRESS")
)
registry_address = required_env("SSI_REGISTRY_ADDRESS")

diploma_path = (
    ROOT
    / "tests"
    / "fixtures"
    / "crypto_ipfs_v1"
    / "diploma.pdf"
)


# --------------------------------------------------
# 2. CONNECT BLOCKCHAIN
# --------------------------------------------------

print("\n[1/6] Connecting to blockchain...")

client = SSIClient(
    rpc_url=rpc_url,
    expected_chain_id=31337,
)

client.require_connection()

actual_issuer = Account.from_key(
    issuer_private_key
).address

if actual_issuer.lower() != issuer_address.lower():
    raise RuntimeError("Issuer private key does not match ISSUER_ADDRESS")

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
issuer_private_pem, issuer_public_pem = verified_pair(registry, issuer_address, ROOT / "keys", "issuer", required_env("ISSUER_RSA_PASSWORD"))


print("Chain ID:", client.w3.eth.chain_id)
print("Issuer:", issuer_address)
print("Registry:", registry.address)


# --------------------------------------------------
# 3. CHECK ISSUER ROLE AND CREDENTIAL STATUS
# --------------------------------------------------

print("\n[2/6] Checking issuer permission and credential...")

issuer_role = registry.functions.ISSUER_ROLE().call()

has_role = registry.functions.hasRole(
    issuer_role,
    issuer_address,
).call()

if not has_role:
    raise RuntimeError("Issuer does not have ISSUER_ROLE")

credential = client.get_credential(
    registry,
    credential_id,
)

# Solidity enum: NONE=0, REQUESTED=1, ISSUED=2, REVOKED=3
if int(credential[9]) != 1:
    raise RuntimeError(
        f"Credential must be REQUESTED (1), current status={credential[9]}"
    )

if credential[1].lower() != "0x0000000000000000000000000000000000000000":
    raise RuntimeError("Credential already has an Issuer")

print("ISSUER_ROLE: PASS")
print("Credential ID:", credential_id)
print("Holder:", credential[0])
print("Status: REQUESTED")


# --------------------------------------------------
# 4. CALCULATE DIPLOMA HASH
# --------------------------------------------------

print("\n[3/6] Calculating diploma SHA-256...")

if not diploma_path.is_file():
    raise FileNotFoundError(diploma_path)

diploma_hash = sha256_bytes(
    diploma_path.read_bytes()
)

if len(diploma_hash) != 32:
    raise RuntimeError("Invalid SHA-256 digest length")

print("Diploma SHA256:", diploma_hash.hex())


# --------------------------------------------------
# 5. GET DIGEST AND SIGN USING EIP-191
# --------------------------------------------------

print("\n[4/6] Signing issuer digest...")

contract_digest = registry.functions.signingDigest(
    credential_id,
    diploma_hash,
).call()

if len(contract_digest) != 32:
    raise RuntimeError("Invalid signingDigest from contract")

message = encode_defunct(
    primitive=contract_digest
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
    raise RuntimeError("EIP-191 signature recovery failed")

print("Contract digest:", contract_digest.hex())
print("Signature length:", len(signature))
print("Recovered signer:", recovered_signer)
print("EIP-191 signature: PASS")


# --------------------------------------------------
# 6. ISSUE CREDENTIAL ON-CHAIN
# --------------------------------------------------

print("\n[5/6] Sending issueCredential transaction...")

receipt = client.send_transaction(
    registry.functions.issueCredential(
        credential_id,
        diploma_hash,
        signature,
    ),
    issuer_private_key,
)

print("Transaction:", receipt["transactionHash"].hex())
print("Block:", receipt["blockNumber"])
print("Transaction status:", receipt["status"])

if receipt["status"] != 1:
    raise RuntimeError("issueCredential transaction failed")


# --------------------------------------------------
# 7. VERIFY ISSUED CREDENTIAL
# --------------------------------------------------

print("\n[6/6] Verifying issued credential...")

updated = client.get_credential(
    registry,
    credential_id,
)

verification = client.verify_credential(
    registry,
    credential_id,
)

if int(updated[9]) != 2:
    raise RuntimeError("Credential status is not ISSUED")

if updated[1].lower() != issuer_address.lower():
    raise RuntimeError("On-chain issuer address mismatch")

if bytes(updated[7]) != diploma_hash:
    raise RuntimeError("On-chain document hash mismatch")

if bytes(updated[8]) != signature:
    raise RuntimeError("On-chain signature mismatch")

if not verification[0]:
    raise RuntimeError("verifyCredential returned false")

print("Credential ID:", credential_id)
print("Issuer:", updated[1])
print("Status: ISSUED (2)")
print("DocHash:", bytes(updated[7]).hex())
print("verifyCredential:", verification)

print("\n======================================")
print("ISSUER CREDENTIAL ISSUANCE: SUCCESS")
print("Credential ID:", credential_id)
print("======================================")
