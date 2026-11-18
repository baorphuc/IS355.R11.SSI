
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
issuer_address = Web3.to_checksum_address(
    required_env("ISSUER_ADDRESS")
)

actual_issuer = Account.from_key(issuer_private_key).address
if actual_issuer.lower() != issuer_address.lower():
    raise RuntimeError("Issuer private key does not match ISSUER_ADDRESS")

registry_artifact = (
    ROOT / "artifacts/contracts/SSIRegistry.sol/SSIRegistry.json"
)
registry = client.load_contract(
    required_env("SSI_REGISTRY_ADDRESS"),
    registry_artifact
)

print("Issuer:", issuer_address)
print("Chain ID:", client.w3.eth.chain_id)

print("\n[2/4] Checking Credential ID 1...")

credential_id = 1
credential = client.get_credential(registry, credential_id)

if int(credential[9]) != 2:
    raise RuntimeError("Credential is not ISSUED")

if credential[1].lower() != issuer_address.lower():
    raise RuntimeError("Current wallet is not the credential issuer")

if credential[12]:
    raise RuntimeError("SBT has already been minted")

holder = Web3.to_checksum_address(credential[0])

print("Credential ID:", credential_id)
print("Status: ISSUED")
print("Holder:", holder)
print("sbtMinted: False")

print("\n[3/4] Sending mintSBT transaction...")

receipt = client.send_transaction(
    registry.functions.mintSBT(credential_id),
    issuer_private_key
)

if receipt["status"] != 1:
    raise RuntimeError("mintSBT transaction failed")

print("Transaction:", receipt["transactionHash"].hex())
print("Block:", receipt["blockNumber"])
print("Transaction status:", receipt["status"])

print("\n[4/4] Verifying SBT...")

updated = client.get_credential(registry, credential_id)

sbt_artifact = (
    ROOT / "artifacts/contracts/IdentitySBT.sol/IdentitySBT.json"
)
sbt = client.load_contract(
    required_env("IDENTITY_SBT_ADDRESS"),
    sbt_artifact
)

balance = sbt.functions.balanceOf(holder).call()
owner = sbt.functions.ownerOf(credential_id).call()

print("Credential ID:", credential_id)
print("sbtMinted:", updated[12])
print("Holder SBT balance:", balance)
print("SBT owner:", owner)

if not updated[12]:
    raise RuntimeError("Credential does not record SBT minted")

if balance != 1:
    raise RuntimeError("Unexpected SBT balance")

if owner.lower() != holder.lower():
    raise RuntimeError("SBT owner does not match Holder")

print("\n======================================")
print("ISSUER SBT MINTING: SUCCESS")
print("Credential ID:", credential_id)
print("======================================")
