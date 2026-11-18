# Chat 02 -> Chat 03: Crypto/IPFS API handoff (Milestone 2)

Baseline: `7227239cff716fc74b5c5ccbe07875be8bb1fc27`.
Status: existing core API, exercised on CPython 3.12.10; no core/ABI/interface change.
The authoritative wire contract remains `interfaces.md` FROZEN v1.

## Frozen formats

- One random 32-byte AES key per dossier, shared by its three files.
- Each file: fresh random 12-byte nonce; AAD exactly `b"ssi-demo-v1"`.
- IPFS bytes: `nonce[12] || ciphertext || tag[16]`; no JSON/base64 wrapper.
- Upload names: `portrait.jpg.enc`, `diploma.pdf.enc`, `metadata.json.enc`.
- RSA generation: 3072 bits, public PEM SubjectPublicKeyInfo, private PEM encrypted PKCS8.
- Key wrapping: OAEP(SHA-256, MGF1-SHA256, label=None).
- Wrapped keys: raw RSA ciphertext bytes (384 bytes for RSA-3072), passed directly
  to Solidity `bytes`. Hex is a display convention only, never UTF-8 encode it.
- `docHash`: raw 32-byte SHA-256 of plaintext `diploma.pdf`, not Keccak or CID.

## Existing Python API

Module `crypto.crypto_utils`:

| Function | Return | Expected errors / responsibility |
|---|---|---|
| `new_aes_key()` | `bytes`, length 32 | Caller creates a new key for each dossier. |
| `generate_rsa_keypair(password: str)` | `(private_pem: bytes, public_pem: bytes)` | `ValueError` for empty password; never log either password or private PEM. Production/demo registration lifecycle is not approved yet. |
| `save_private_pem(path: Path, private_pem: bytes)` | `None` | Filesystem `OSError`; caller must supply encrypted PEM. Helper does not validate PEM encryption. `chmod(0600)` is best effort, not proof of Windows ACL protection. |
| `encrypt_bytes(plaintext: bytes, key: bytes, associated_data=b"ssi-demo-v1")` | Frozen wire bytes | `ValueError` for non-32-byte key; non-default AAD cannot be packed as v1. Use only the default AAD. |
| `decrypt_bytes(payload: bytes, key: bytes, associated_data=b"ssi-demo-v1")` | Plaintext bytes after successful authentication | `EncryptedPackageError` for short/invalid payload, AAD mismatch, wrong AES key, changed nonce/ciphertext/tag; `ValueError` for invalid AES length. No partial plaintext is returned. |
| `encrypt_package(plaintext, key, associated_data=b"ssi-demo-v1")` | `EncryptedPackage` | Same key validation; call `.pack()` before upload. Keep AAD default. |
| `EncryptedPackage.unpack(payload)` | `EncryptedPackage` | `EncryptedPackageError` for wrong type or fewer than 28 bytes. Structural parsing alone does not authenticate ciphertext. |
| `decrypt_package(package, key, associated_data=b"ssi-demo-v1")` | Plaintext bytes | `EncryptedPackageError` for invalid package/version/algorithm/nonce/tag/AAD or GCM authentication failure. |
| `wrap_key(aes_key, public_pem)` | Raw RSA ciphertext bytes | `ValueError` for invalid AES length, malformed/non-RSA public PEM; current core accepts imported RSA-2048 too. Validate the FROZEN RSA-3072 constraint at integration; do not silently adopt another key size. |
| `wrap_key_for_roles(aes_key, holder_public_pem, issuer_public_pem)` | `(wrappedKeyForHolder, wrappedKeyForIssuer)` | Same AES key wrapped independently for each public key; same errors as `wrap_key`. |
| `unwrap_key(wrapped_key, private_pem, password)` | AES key, 32 bytes | `ValueError` for empty/invalid wrapped key, empty/wrong password, invalid/non-RSA private PEM, wrong RSA key, OAEP failure or recovered AES length mismatch. Invalid Python argument types can also raise `TypeError`. |
| `sha256_bytes(data)` | Digest bytes, length 32 | Caller compares against credential `docHash`; helper does not fetch chain state or reject a mismatched hash automatically. |

`EncryptedPackageError` subclasses `ValueError`. Authentication error text cannot
reliably distinguish a wrong key from tampering; show a neutral failure message.
Treat invalid file/key types as validation failures before calling helpers.

Module `ipfs.kubo_client`:

| API | Return | Expected errors / responsibility |
|---|---|---|
| `KuboClient(api_url="http://127.0.0.1:5001", timeout=30, session=None)` | Client | Keep Kubo RPC on loopback; it is an administrative API. Do not expose it publicly. |
| `add_bytes(data: bytes, filename: str)` | CID string; Kubo add requests `pin=true` | `ValueError`: non-`.enc` name or empty data; `KuboConnectionError`: timeout/network; `KuboResponseError`: HTTP/non-JSON/missing Hash; `InvalidCIDError`: rejected CID. |
| `add_encrypted(path: Path)` | CID string | Same transport errors plus filesystem `OSError` and suffix validation. Reads the whole file into memory. |
| `cat(cid: str)` | Downloaded bytes | `InvalidCIDError`, `KuboConnectionError`, `KuboResponseError` for HTTP/empty data. Does not decrypt or enforce consent. |

Known baseline defects intentionally not changed by this milestone: CID validation
is only a loose string check; JSON list/null from `add` can raise `AttributeError`;
renaming plaintext to `.enc` is not encryption. Encrypt before calling `add_bytes`.
The milestone does not silently turn these into a new API contract.

## Holder/Issuer integration sequence

1. Receive exactly three validated synthetic files. Create one AES key.
2. Calculate `docHash = sha256_bytes(diploma_plaintext)`.
3. Wrap that AES key independently for the selected Holder and Issuer RSA public keys.
4. `encrypt_bytes()` each file, `client.add_bytes()` each wire payload.
5. Pass three CID strings and the two wrapped `bytes` to `requestCredential`.
6. On reopening: get the credential, unwrap the appropriate role's wrapped key.
7. For each CID, call `retrieved = client.cat(cid)` then
   `plaintext = decrypt_bytes(retrieved, recovered_key)`.
8. Issuer validates the recovered files and computes SHA-256 PDF for issuance.
   Holder/Verifier compare the recovered PDF against `docHash` read from chain.
9. EIP-191 signing of the frozen 32-byte digest is Chat 03 responsibility;
   these crypto helpers do not implement signing or choose the Issuer.

## Verifier/consent boundary (handoff only, not executed here)

- Public `verifyCredential` does not require consent.
- Before the supported decrypt flow, Chat 03 checks the current credential state,
  `hasAccess(credentialId, verifierAddress)` and active `getConsent` result.
- Holder unwraps its own copy and calls existing `wrap_key(aes_key, verifier_public_pem)`
  to prepare `wrappedKeyForVerifier`, then submits `grantConsent` through Chat 03.
- Verifier uses its own RSA PEM/password with `unwrap_key`, retrieves/decrypts
  the actual returned ciphertext, and compares PDF SHA-256 to on-chain `docHash`.
- On inactive/revoked consent, Chat 03 rejects a new supported decrypt operation.
  This is application policy, not a restriction imposed by Kubo or crypto helpers.
- Historical wrapped keys and already disclosed plaintext/AES keys cannot be
  cryptographically revoked by toggling consent. Do not claim otherwise.
- No registry/key-registration workflow is implemented. DL-05 remains PROPOSED.

## Evidence references

- `evidence/m2/run-02/baseline-unit.log`: 44 baseline tests.
- `evidence/m2/run-02/all-unit.log`: 59 tests including 15 M2 cases.
- `evidence/m2/run-02/real-kubo.log` and `real-kubo/result.json`: real Kubo
  HTTP add/cat through the unchanged Python client; Holder and Issuer decode all
  three retrieved files, render PDF and compare PDF SHA-256.
- No consent/on-chain/UI acceptance is implied by these results.
