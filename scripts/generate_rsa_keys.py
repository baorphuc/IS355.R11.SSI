
import sys
from pathlib import Path
from dotenv import dotenv_values

# Đưa thư mục gốc dự án vào Python import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crypto.crypto_utils import generate_rsa_keypair, save_private_pem

KEYS_DIR = ROOT / "keys"
ENV = dotenv_values(ROOT / ".env")

KEYS_DIR.mkdir(exist_ok=True)

ROLES = {
    "holder": "HOLDER_RSA_PASSWORD",
    "issuer": "ISSUER_RSA_PASSWORD",
}

for role, env_name in ROLES.items():
    password = ENV.get(env_name)

    if not password:
        raise ValueError(f"Thiếu {env_name} trong .env")

    private_pem, public_pem = generate_rsa_keypair(password)

    save_private_pem(KEYS_DIR / f"{role}_private.pem", private_pem)
    (KEYS_DIR / f"{role}_public.pem").write_bytes(public_pem)

    print(f"{role.capitalize()} RSA keypair generated successfully")

print("RSA key generation completed.")
