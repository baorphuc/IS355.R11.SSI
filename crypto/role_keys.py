"""Role-specific RSA keys for the frozen SSI demo interface."""
import hashlib
import os
import subprocess

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from crypto.crypto_utils import generate_rsa_keypair, save_private_pem

ROLES = ("holder", "issuer", "verifier")
SPKI = serialization.PublicFormat.SubjectPublicKeyInfo


def paths(directory, role):
    if role not in ROLES:
        raise ValueError("Unknown RSA role")
    return directory / f"{role}_private.pem", directory / f"{role}_public.pem"


def public_key(pem):
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size != 3072:
        raise ValueError("Expected RSA-3072")
    return key


def fingerprint(pem):
    return hashlib.sha256(public_key(pem).public_bytes(serialization.Encoding.DER, SPKI)).hexdigest()


def create_pair(directory, role, password):
    private, public = paths(directory, role)
    existing = [os.path.lexists(path) for path in (private, public)]
    if any(existing):
        raise FileExistsError("RSA pair already exists" if all(existing) else "Incomplete RSA pair; restore backup")
    secret, pem = generate_rsa_keypair(password)
    save_private_pem(private, secret)
    with public.open("xb") as target:
        target.write(pem)
    return fingerprint(pem)


def load_pair(directory, role, password):
    private, public = paths(directory, role)
    if not private.is_file() or not public.is_file():
        raise FileNotFoundError("Missing RSA pair; restore both PEM files")
    if private.is_symlink() or public.is_symlink():
        raise ValueError("Linked PEM file")
    if os.name != "nt" and private.stat().st_mode & 0o077:
        raise PermissionError("Private PEM requires owner-only permissions")
    if os.name == "nt":
        # Reject permissions granted to Everyone, Authenticated Users or the Users group.
        command = """$ErrorActionPreference='Stop'
$rules=([IO.File]::GetAccessControl($env:SSI_PEM_ACL_PATH)).GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
foreach($r in $rules){if($r.AccessControlType -eq 'Allow' -and $r.IdentityReference.Value -in 'S-1-1-0','S-1-5-11','S-1-5-32-545' -and ([int]$r.FileSystemRights -band 1)){exit 2}}"""
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                env={**os.environ, "SSI_PEM_ACL_PATH": str(private)},
                                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise PermissionError("Check the Windows ACL on the private PEM")
    secret = private.read_bytes()
    pem = public.read_bytes()
    key = serialization.load_pem_private_key(secret, password=password.encode())
    if not isinstance(key, rsa.RSAPrivateKey) or key.public_key().public_numbers() != public_key(pem).public_numbers():
        raise ValueError("Private/public RSA pair mismatch")
    return secret, public_key(pem).public_bytes(serialization.Encoding.PEM, SPKI)
