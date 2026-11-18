
import os
from pathlib import Path
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3
from web3_client.client import SSIClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def required_env(name):
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"Missing environment variable: {name}")
    return value.strip()


print("\n[1/4] Connecting to blockchain...")

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

artifact = (
    ROOT / "artifacts/contracts/SSIRegistry.sol/SSIRegistry.json"
)
registry = client.load_contract(
    required_env("SSI_REGISTRY_ADDRESS"),
    artifact
)

credential_id = 1

print("Holder:", holder_address)
print("Verifier:", verifier_address)


print("\n[2/4] Checking current consent...")

active_before, wrapped_before = registry.functions.getConsent(
    credential_id,
    verifier_address
).call()

has_access_before = registry.functions.hasAccess(
    credential_id,
    verifier_address
).call()

print("Consent active before:", active_before)
print("hasAccess before:", has_access_before)

if not active_before or not has_access_before:
    raise RuntimeError("Verifier does not currently have active consent")


print("\n[3/4] Revoking consent...")

receipt = client.send_transaction(
    registry.functions.revokeConsent(
        credential_id,
        verifier_address
    ),
    holder_private_key
)

if receipt["status"] != 1:
    raise RuntimeError("revokeConsent transaction failed")

print("Transaction:", receipt["transactionHash"].hex())
print("Block:", receipt["blockNumber"])


print("\n[4/4] Verifying revoked consent...")

active_after, wrapped_after = registry.functions.getConsent(
    credential_id,
    verifier_address
).call()

has_access_after = registry.functions.hasAccess(
    credential_id,
    verifier_address
).call()

if active_after:
    raise RuntimeError("FAIL: Consent is still active")

if has_access_after:
    raise RuntimeError("FAIL: Verifier still has access")

if bytes(wrapped_after) != bytes(wrapped_before):
    raise RuntimeError("Unexpected change in stored wrapped key")

print("Consent active after:", active_after)
print("hasAccess after:", has_access_after)
print("Stored wrapped key retained:", len(wrapped_after), "bytes")
print("New access blocked: PASS")

print("\n======================================")
print("HOLDER REVOKE CONSENT: SUCCESS")
print("Verifier access revoked")
print("======================================")
