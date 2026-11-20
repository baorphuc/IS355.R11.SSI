import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values
from crypto.role_keys import ROLES, create_pair


def main():
    parser = argparse.ArgumentParser(description="Create one new role key pair; existing PEMs are protected.")
    parser.add_argument("--create", choices=ROLES, required=True)
    role = parser.parse_args().create
    password = dotenv_values(ROOT / ".env").get(role.upper() + "_RSA_PASSWORD")
    if not password:
        parser.error("Missing RSA password for selected role")
    try:
        print(role, create_pair(ROOT / "keys", role, password))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
