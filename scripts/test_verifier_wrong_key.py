
import os
from pathlib import Path
from dotenv import load_dotenv

from crypto.crypto_utils import unwrap_key
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

artifact = (
    ROOT / "artifacts/contracts/SSIRegistry.sol/SSIRegistry.json"
)
registry = client.load_contract(
    required_env("SSI_REGISTRY_ADDRESS"),
    artifact
)

credential_id = 1
verifier_address = required_env("VERIFIER_ADDRESS")

print("Credential ID:", credential_id)
print("Verifier:", verifier_address)

print("\n[2/3] Reading Verifier wrapped key...")

active, wrapped_key = registry.functions.getConsent(
    credential_id,
    verifier_address
).call()

if not active:
    raise RuntimeError("Verifier consent is not active")

wrapped_key = bytes(wrapped_key)

print("Consent active: True")
print("Wrapped key length:", len(wrapped_key))

print("\n[3/3] Trying wrong RSA private key...")

wrong_private_pem = (
    ROOT / "keys" / "issuer_private.pem"
).read_bytes()

issuer_password = required_env("ISSUER_RSA_PASSWORD")

try:
    unwrap_key(
        wrapped_key,
        wrong_private_pem,
        issuer_password
    )
except Exception as exc:
    print("Wrong key rejected:", type(exc).__name__)
    print("RSA wrong-key protection: PASS")
else:
    raise RuntimeError(
        "FAIL: Wrong private key unexpectedly decrypted AES key"
    )

print("\n======================================")
print("VERIFIER WRONG RSA KEY: PASS")
print("AES key recovery correctly rejected")
print("======================================")
