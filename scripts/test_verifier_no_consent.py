
import os
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3_client.client import SSIClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def required_env(name):
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"Missing environment variable: {name}")
    return value.strip()


print("\n[1/3] Connecting to blockchain...")

client = SSIClient(
    rpc_url=required_env("LOCAL_RPC_URL"),
    expected_chain_id=31337
)
client.require_connection()

registry_artifact = (
    ROOT / "artifacts/contracts/SSIRegistry.sol/SSIRegistry.json"
)
registry = client.load_contract(
    required_env("SSI_REGISTRY_ADDRESS"),
    registry_artifact
)

unauthorized_verifier = Web3.to_checksum_address(
    "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
)

credential_id = 1

print("Chain ID:", client.w3.eth.chain_id)
print("Credential ID:", credential_id)
print("Unauthorized Verifier:", unauthorized_verifier)


print("\n[2/3] Checking unauthorized access...")

has_access = registry.functions.hasAccess(
    credential_id,
    unauthorized_verifier
).call()

active, wrapped_key = registry.functions.getConsent(
    credential_id,
    unauthorized_verifier
).call()

print("hasAccess:", has_access)
print("Consent active:", active)
print("Wrapped key length:", len(wrapped_key))


print("\n[3/3] Evaluating security checks...")

if has_access:
    raise RuntimeError("FAIL: Unauthorized Verifier has access!")

if active:
    raise RuntimeError("FAIL: Unauthorized Verifier has active consent!")

if len(wrapped_key) != 0:
    raise RuntimeError(
        "Unexpected wrapped key exists. Investigate contract state."
    )

print("Unauthorized access: BLOCKED")
print("Consent check: PASS")
print("Wrapped key disclosure: BLOCKED")

print("\n======================================")
print("VERIFIER WITHOUT CONSENT: PASS")
print("Unauthorized Verifier cannot access Credential")
print("======================================")
