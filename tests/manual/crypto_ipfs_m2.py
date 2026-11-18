"""Real Kubo acceptance runner. No mocks, no persisted cryptographic keys.

Run with -u and redirect stdout/stderr to a raw log. This script never registers
RSA public keys or sends Ethereum transactions. DL-05 remains PROPOSED.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import secrets
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pymupdf
import requests
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from crypto.crypto_utils import (
    EncryptedPackage, decrypt_bytes, encrypt_bytes, generate_rsa_keypair,
    new_aes_key, sha256_bytes, unwrap_key, wrap_key_for_roles,
)
from ipfs.kubo_client import KuboClient

BASELINE = "7227239cff716fc74b5c5ccbe07875be8bb1fc27"
NAMES = ("portrait.jpg", "diploma.pdf", "metadata.json")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_file(name: str, data: bytes, render_path: Path | None = None) -> dict:
    if name == "portrait.jpg":
        with Image.open(io.BytesIO(data)) as image:
            assert image.format == "JPEG"
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            assert image.size == (320, 240)
            return {"format": "JPEG", "width": image.width, "height": image.height,
                    "decoded": True}
    if name == "diploma.pdf":
        with pymupdf.open(stream=data, filetype="pdf") as document:
            assert len(document) == 1 and not document.is_encrypted
            assert "SYNTHETIC TEST DOCUMENT" in document[0].get_text()
            pix = document[0].get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
            assert pix.width > 0 and pix.height > 0
            if render_path:
                pix.save(render_path)
            return {"format": "PDF", "pages": len(document), "decoded": True,
                    "rendered": True, "pixels": [pix.width, pix.height]}
    parsed = json.loads(data.decode("utf-8"))
    assert parsed == {"schema": "ssi-demo-fixture-v1", "synthetic": True,
                      "documentType": "test-diploma", "fixtureId": "M2-0001",
                      "containsPII": False}
    return {"format": "JSON", "utf8": True, "parsed": True, "containsPII": False}


def generate_fixtures(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (320, 240), (231, 240, 248))
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 303, 223), outline=(32, 69, 103), width=3)
    draw.ellipse((132, 48, 188, 104), fill=(60, 106, 142))
    draw.rectangle((112, 112, 208, 168), fill=(60, 106, 142))
    draw.text((75, 190), "SYNTHETIC - NO REAL PERSON", fill=(20, 40, 60))
    image.save(directory / "portrait.jpg", format="JPEG", quality=90, optimize=False)
    pdf = canvas.Canvas(str(directory / "diploma.pdf"), pagesize=(595, 842),
                        invariant=1, pageCompression=1)
    pdf.setTitle("SSI M2 synthetic fixture - not a real credential")
    pdf.setAuthor("SSI test fixture generator")
    pdf.setFont("Helvetica-Bold", 23)
    pdf.drawString(55, 745, "SYNTHETIC TEST DOCUMENT")
    pdf.setFont("Helvetica", 13)
    for y, line in [(695, "SSI Crypto & IPFS Milestone 2"),
                    (665, "Fixture M2-0001: encryption and integrity testing only."),
                    (635, "No holder name, student number, or personal information."),
                    (605, "This document is not a qualification or credential.")]:
        pdf.drawString(55, y, line)
    pdf.showPage()
    pdf.save()
    metadata = {"schema": "ssi-demo-fixture-v1", "synthetic": True,
                "documentType": "test-diploma", "fixtureId": "M2-0001",
                "containsPII": False}
    (directory / "metadata.json").write_text(
        json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    inventory = {}
    for name in NAMES:
        data = (directory / name).read_bytes()
        inventory[name] = {"bytes": len(data), "sha256": digest(data),
                           "validation": validate_file(name, data)}
    (directory / "inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"event": "fixtures_generated", "inventory": inventory}), flush=True)
    return inventory


def run_real_kubo(api: str, fixtures: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    client = KuboClient(api_url=api, timeout=30)
    response = requests.post(f"{api.rstrip('/')}/api/v0/version", timeout=10)
    response.raise_for_status()
    kubo_version = response.json()
    print(json.dumps({"event": "real_kubo_version", "response": kubo_version}), flush=True)
    bundle_key = new_aes_key()
    # Disposable passwords/keys exist in memory only. They are never logged.
    holder_password, issuer_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    holder_private, holder_public = generate_rsa_keypair(holder_password)
    issuer_private, issuer_public = generate_rsa_keypair(issuer_password)
    wrapped_holder, wrapped_issuer = wrap_key_for_roles(bundle_key, holder_public, issuer_public)
    holder_key = unwrap_key(wrapped_holder, holder_private, holder_password)
    issuer_key = unwrap_key(wrapped_issuer, issuer_private, issuer_password)
    assert holder_key == issuer_key == bundle_key
    assert len(wrapped_holder) == len(wrapped_issuer) == 384
    assert wrapped_holder != wrapped_issuer
    pdf_hash = sha256_bytes((fixtures / "diploma.pdf").read_bytes())
    nonces, results = set(), {}
    for name in NAMES:
        plaintext = (fixtures / name).read_bytes()
        validate_file(name, plaintext)
        encrypted = encrypt_bytes(plaintext, bundle_key)
        nonce = EncryptedPackage.unpack(encrypted).nonce
        assert nonce not in nonces
        nonces.add(nonce)
        cid = client.add_bytes(encrypted, name + ".enc")
        # This is the actual Kubo HTTP result, not a local encrypted file.
        retrieved = client.cat(cid)
        assert retrieved == encrypted
        (output / (name + ".enc")).write_bytes(retrieved)
        pin = requests.post(f"{api.rstrip('/')}/api/v0/pin/ls",
                            params={"arg": cid}, timeout=10)
        pin.raise_for_status()
        assert cid in pin.json()["Keys"]
        for role, key in (("holder", holder_key), ("issuer", issuer_key)):
            recovered = decrypt_bytes(retrieved, key)
            assert recovered == plaintext
            role_path = output / role
            role_path.mkdir(exist_ok=True)
            file_path = role_path / name
            file_path.write_bytes(recovered)
            # Reopen the recovered file from disk; decode JPEG, render PDF, parse JSON.
            validation = validate_file(name, file_path.read_bytes(),
                                       role_path / "diploma-preview.png" if name == "diploma.pdf" else None)
            if name == "diploma.pdf":
                assert sha256_bytes(file_path.read_bytes()) == pdf_hash
            print(json.dumps({"event": "reopened_recovered_file", "role": role,
                              "file": name, "validation": validation}), flush=True)
        results[name] = {"cid": cid, "plaintext_bytes": len(plaintext),
                         "ciphertext_bytes": len(retrieved), "plaintext_sha256": digest(plaintext),
                         "ciphertext_sha256": digest(retrieved), "retrieved_equals_uploaded": True,
                         "holder_decrypt": True, "issuer_decrypt": True, "pinned": True}
        print(json.dumps({"event": "file_pass", "file": name, **results[name]}), flush=True)
    result = {"baseline": BASELINE, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "mock": False, "api": api, "kubo_version": kubo_version,
              "docHash": pdf_hash.hex(), "nonce_count": len(nonces),
              "wrapped_key_lengths": [len(wrapped_holder), len(wrapped_issuer)],
              "files": results, "keys_persisted": False,
              "consent_tested": False, "DL-05": "PROPOSED; no registration workflow implemented"}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"event": "REAL_KUBO_PASS", "result": result}), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=ROOT / "tests/fixtures/crypto_ipfs_v1")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/m2/real-kubo")
    parser.add_argument("--api", default="http://127.0.0.1:15001")
    parser.add_argument("--generate-fixtures", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"event": "environment", "python": sys.version,
                      "platform": platform.platform(), "baseline": BASELINE,
                      "packages": {p: version(p) for p in
                          ("cryptography", "requests", "pytest", "Pillow", "PyMuPDF", "reportlab")}}), flush=True)
    if args.generate_fixtures:
        generate_fixtures(args.fixtures)
    else:
        run_real_kubo(args.api, args.fixtures, args.output)


if __name__ == "__main__":
    main()
