
import hashlib
from pathlib import Path

from crypto.crypto_utils import new_aes_key, encrypt_bytes, decrypt_bytes
from ipfs.kubo_client import KuboClient

FIXTURES = Path("tests/fixtures/crypto_ipfs_v1")
FILES = ["portrait.jpg", "diploma.pdf", "metadata.json"]

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main():
    client = KuboClient(api_url="http://127.0.0.1:5001")
    key = new_aes_key()

    print("Starting IPFS encryption round-trip test...")

    for filename in FILES:
        original = (FIXTURES / filename).read_bytes()

        # Encrypt using AES-GCM
        encrypted = encrypt_bytes(original, key)

        # Upload encrypted bytes to IPFS
        cid = client.add_bytes(encrypted, filename + ".enc")

        # Download encrypted bytes from IPFS
        downloaded = client.cat(cid)

        # Verify ciphertext integrity
        assert downloaded == encrypted, f"{filename}: ciphertext mismatch"

        # Decrypt and verify plaintext
        recovered = decrypt_bytes(downloaded, key)
        assert recovered == original, f"{filename}: plaintext mismatch"

        print(f"\n{filename}: PASS")
        print(f"  CID: {cid}")
        print(f"  Original SHA256: {sha256(original)}")
        print(f"  Recovered SHA256: {sha256(recovered)}")
        print(f"  Encrypted bytes: {len(encrypted)}")
        print("  Upload / Download / Decrypt: PASS")

    print("\nALL 3 FILES PASSED.")

if __name__ == "__main__":
    main()
