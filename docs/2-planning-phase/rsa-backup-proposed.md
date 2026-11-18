# RSA encrypted PEM backup / fingerprint preparation

Status: PREPARATION ONLY. DL-05 is PROPOSED, not approved. This document neither
registers a key nor makes public keys immutable. No rotation/versioning/rewrap
workflow has been implemented. Do not perform on-chain registration on its basis.

## Fingerprint convention for PM/Chat 03 review

Candidate display fingerprint: SHA-256 of the DER-encoded SubjectPublicKeyInfo
public key, hex encoded. DER avoids differences due only to PEM whitespace.
This fingerprint is a local display/check value; it adds no field to FROZEN v1
and is not the credential `docHash` or an Ethereum address.

```python
from cryptography.hazmat.primitives import serialization
from crypto.crypto_utils import sha256_bytes

def public_fingerprint(public_pem: bytes) -> str:
    public_key = serialization.load_pem_public_key(public_pem)
    der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return sha256_bytes(der).hex()
```

## Proposed local backup checklist

1. Keep Holder/Issuer/Verifier RSA pairs separate from each other and from
   Ethereum wallet keys. Never put a wallet secret into a PEM field.
2. Generate RSA-3072 with a strong nonempty password; verify the private PEM is
   encrypted PKCS8. Keep passwords outside source/logs. FROZEN v1 specifies the
   role-specific environment variable names for the eventual demo application.
3. Record only the public fingerprint and role in a public checklist. Do not
   include the password, private PEM, AES key or wrapped-key plaintext.
4. Copy the encrypted PEM to an authorized offline/encrypted backup destination;
   keep password recovery separate. The actual destination/custodian is a PM
   decision and no personal key backup has been performed by this milestone.
5. Restrict local and backup filesystem permissions. On Windows, explicitly
   inspect ACLs; the helper's `chmod(0600)` does not demonstrate correct ACLs.
6. Restore a copy into a private temporary location and load it using its
   password. Re-derive the public DER fingerprint and compare with the recorded
   one. Wrap/unwrap a new disposable AES key as a recovery smoke test.
7. Never delete the only functioning encrypted private key. If lost, old wrapped
   AES keys are not recoverable by a password reset or contract transaction.

The M2 automated test verifies encrypted PEM load and public fingerprint equality
using in-memory disposable keys only; it does not prove a user's backup/storage
or recovery process and does not implement registration.

## Dependency requiring PM approval

DL-05: confirm or reject the proposed immutable public-key / no-rotation policy,
with A/B agreement and C/D UX/test review. Until then, one-time registration guards,
update prevention and any UI registration flow stay deferred. The public
fingerprint display convention and local backup custodian/destination are also
awaiting integration review. This dependency does not block fixture/Kubo tests.
