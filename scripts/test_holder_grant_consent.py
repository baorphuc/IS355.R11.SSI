from web3_client.role_keys import verified_pair, verify_public

import os
from pathlib import Path
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

from crypto.crypto_utils import unwrap_key, wrap_key
from web3_client.client import SSIClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def required_env(name):
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"Missing environment variable: {name}")
    return value.strip()


print("\n[1/5] Connecting to blockchain...")

client = SSIClient(
    rpc_url=required_env("LOCAL_RPC_URL"),
    expected_chain_id=31337
)
client.require_connection()

holder_private_key = required_env("HOLDER_PRIVATE_KEY")
holder_address = Account.from_key(holder_private_key).address

verifier_address = Web3.to_checksum_address(
    required_env("VERIFIER_ADDRESS")
)

registry_artifact = (
    ROOT / "artifacts/contracts/SSIRegistry.sol/SSIRegistry.json"
)
registry = client.load_contract(
    required_env("SSI_REGISTRY_ADDRESS"),
    registry_artifact
)
holder_private_pem, holder_public_pem = verified_pair(registry, holder_address, ROOT / "keys", "holder", required_env("HOLDER_RSA_PASSWORD"))
verifier_public_pem = verify_public(registry, verifier_address, (ROOT / "keys" / "verifier_public.pem").read_bytes())


print("Chain ID:", client.w3.eth.chain_id)
print("Holder:", holder_address)
print("Verifier:", verifier_address)

print("\n[2/5] Checking Credential ID 1...")

credential_id = 1
credential = client.get_credential(registry, credential_id)

if credential[0].lower() != holder_address.lower():
    raise RuntimeError("Current wallet is not the credential Holder")

if int(credential[9]) != 2:
    raise RuntimeError("Credential is not ISSUED")

if not credential[12]:
    raise RuntimeError("Credential SBT has not been minted")

print("Credential ID:", credential_id)
print("Status: ISSUED")
print("SBT minted:", credential[12])

print("\n[3/5] Recovering AES key for Holder...")

holder_password = required_env("HOLDER_RSA_PASSWORD")

wrapped_holder_key = bytes(credential[5])

if len(wrapped_holder_key) != 384:
    raise RuntimeError("Invalid Holder wrapped key length")

aes_key = unwrap_key(
    wrapped_holder_key,
    holder_private_pem,
    holder_password
)

if len(aes_key) != 32:
    raise RuntimeError("Recovered AES key has invalid length")

print("Holder wrapped key: 384 bytes")
print("AES key recovered: PASS")

print("\n[4/5] Wrapping AES key for Verifier...")


wrapped_verifier_key = wrap_key(
    aes_key,
    verifier_public_pem
)

if len(wrapped_verifier_key) != 384:
    raise RuntimeError("Invalid Verifier wrapped key length")

print("Verifier wrapped key: 384 bytes")

print("\n[5/5] Granting on-chain consent...")

existing_active, _ = registry.functions.getConsent(
    credential_id,
    verifier_address
).call()

if existing_active:
    raise RuntimeError(
        "Consent is already active. Refusing to send duplicate transaction."
    )

receipt = client.send_transaction(
    registry.functions.grantConsent(
        credential_id,
        verifier_address,
        wrapped_verifier_key
    ),
    holder_private_key
)

if receipt["status"] != 1:
    raise RuntimeError("grantConsent transaction failed")

print("Transaction:", receipt["transactionHash"].hex())
print("Block:", receipt["blockNumber"])

print("\nVerifying consent...")

has_access = registry.functions.hasAccess(
    credential_id,
    verifier_address
).call()

active, stored_wrapped_key = registry.functions.getConsent(
    credential_id,
    verifier_address
).call()

if not has_access or not active:
    raise RuntimeError("Consent verification failed")

if bytes(stored_wrapped_key) != wrapped_verifier_key:
    raise RuntimeError("Stored wrapped key does not match")

print("hasAccess:", has_access)
print("Consent active:", active)
print("Stored wrapped key: MATCH")

print("\n======================================")
print("HOLDER GRANT CONSENT: SUCCESS")
print("Credential ID:", credential_id)
print("======================================")
