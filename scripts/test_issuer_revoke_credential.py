
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

issuer_private_key = required_env("ISSUER_PRIVATE_KEY")
issuer_address = Account.from_key(issuer_private_key).address

registry_artifact = (
    ROOT / "artifacts/contracts/SSIRegistry.sol/SSIRegistry.json"
)

registry = client.load_contract(
    required_env("SSI_REGISTRY_ADDRESS"),
    registry_artifact
)

credential_id = 1

print("Issuer:", issuer_address)
print("Credential ID:", credential_id)


print("\n[2/4] Checking current Credential...")

credential = client.get_credential(registry, credential_id)
verification_before = registry.functions.verifyCredential(
    credential_id
).call()

if int(credential[9]) != 2:
    raise RuntimeError("Credential is not ISSUED")

if credential[1].lower() != issuer_address.lower():
    raise RuntimeError("Current wallet is not the credential Issuer")

if not verification_before[0]:
    raise RuntimeError("Credential is not currently valid")

print("Status before:", int(credential[9]))
print("verifyCredential before:", verification_before[0])
print("SBT minted before:", credential[12])


print("\n[3/4] Revoking Credential...")

receipt = client.send_transaction(
    registry.functions.revokeCredential(credential_id),
    issuer_private_key
)

if receipt["status"] != 1:
    raise RuntimeError("revokeCredential transaction failed")

print("Transaction:", receipt["transactionHash"].hex())
print("Block:", receipt["blockNumber"])


print("\n[4/4] Verifying revoked Credential...")

updated = client.get_credential(registry, credential_id)

verification_after = registry.functions.verifyCredential(
    credential_id
).call()

has_access = registry.functions.hasAccess(
    credential_id,
    required_env("VERIFIER_ADDRESS")
).call()

sbt_address = required_env("IDENTITY_SBT_ADDRESS")
sbt_artifact = (
    ROOT / "artifacts/contracts/IdentitySBT.sol/IdentitySBT.json"
)

sbt = client.load_contract(sbt_address, sbt_artifact)

holder = updated[0]
balance = sbt.functions.balanceOf(holder).call()

print("Status after:", int(updated[9]))
print("verifyCredential after:", verification_after[0])
print("hasAccess after:", has_access)
print("sbtMinted after:", updated[12])
print("Holder SBT balance after:", balance)

if int(updated[9]) != 3:
    raise RuntimeError("Credential status is not REVOKED")

if verification_after[0]:
    raise RuntimeError("Revoked Credential is still valid")

if has_access:
    raise RuntimeError("Verifier still has access")

if updated[12]:
    raise RuntimeError("SBT was not marked as burned")

if balance != 0:
    raise RuntimeError("Holder still owns the revoked SBT")

print("\n======================================")
print("ISSUER REVOKE CREDENTIAL: SUCCESS")
print("Credential ID:", credential_id)
print("Status: REVOKED")
print("SBT: BURNED")
print("======================================")
