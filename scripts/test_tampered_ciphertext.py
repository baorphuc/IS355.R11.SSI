
import os
from pathlib import Path
from dotenv import load_dotenv

from crypto.crypto_utils import unwrap_key, decrypt_bytes
from ipfs.kubo_client import KuboClient
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


print("\n[2/4] Recovering valid AES key...")

credential = client.get_credential(registry, credential_id)

active, wrapped_key = registry.functions.getConsent(
    credential_id,
    verifier_address
).call()

if not active:
    raise RuntimeError("Verifier consent is not active")

verifier_private_pem = (
    ROOT / "keys" / "verifier_private.pem"
).read_bytes()

aes_key = unwrap_key(
    bytes(wrapped_key),
    verifier_private_pem,
    required_env("VERIFIER_RSA_PASSWORD")
)

print("AES key recovery: PASS")


print("\n[3/4] Downloading and tampering ciphertext...")

kubo = KuboClient(api_url=required_env("IPFS_API_URL"))

diploma_cid = credential[3]
encrypted = bytearray(kubo.cat(diploma_cid))

if len(encrypted) <= 28:
    raise RuntimeError("Ciphertext is too short")

# Chỉ sửa một byte trong ciphertext, giữ nguyên dữ liệu IPFS gốc.
tampered = bytearray(encrypted)
tampered[20] ^= 0x01

if tampered == encrypted:
    raise RuntimeError("Tampering operation failed")

print("Original ciphertext bytes:", len(encrypted))
print("Tampered ciphertext bytes:", len(tampered))
print("Original IPFS data unchanged: True")


print("\n[4/4] Trying AES-GCM decryption...")

try:
    decrypt_bytes(bytes(tampered), aes_key)
except Exception as exc:
    print("Tampered ciphertext rejected:", type(exc).__name__)
    print("AES-GCM integrity protection: PASS")
else:
    raise RuntimeError(
        "FAIL: Tampered ciphertext was decrypted successfully"
    )

print("\n======================================")
print("TAMPERED CIPHERTEXT TEST: PASS")
print("AES-GCM rejected modified ciphertext")
print("======================================")
