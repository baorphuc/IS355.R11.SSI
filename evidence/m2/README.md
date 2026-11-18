# Milestone 2 - Chat 02 Crypto & IPFS evidence

Run date: 17 November 2026, Asia/Saigon (successful run approximately 15:16).
Baseline archive comment: `7227239cff716fc74b5c5ccbe07875be8bb1fc27`.
Result: baseline unit PASS, expanded security/fixture unit PASS, real local
offline Kubo PASS. This is not PM/D final acceptance or consent/on-chain acceptance.

## Actual test results

| Run | Baseline unit | All unit after M2 additions | Real Kubo |
|---|---:|---:|---|
| `run-01` | 44 passed | 59 passed | NOT_RUN: API could not be reached from execution context; raw failure retained |
| `run-02` | 44 passed | 59 passed | PASS through unchanged `KuboClient` and real Python requests |

`run-01` ran in the restricted terminal context; Kubo started but its API was
unreachable to the Python caller. `run-02` ran the same Python runner from the
available host execution context with loopback connectivity. No transport was
mocked or replaced. Both attempts' original logs and commands remain present.
The successful dedicated daemon was shut down after the test with exit code 0.

## Environment

- Windows amd64; isolated official portable CPython 3.12.10, installed packages
  exactly pinned in `requirements-crypto-ipfs-m2.lock.txt`.
- cryptography 46.0.3; requests 2.32.5; pytest 8.4.2.
- Pillow 12.0.0 for JPEG decoding; ReportLab 4.4.5 for deterministic synthetic PDF;
  PyMuPDF 1.26.6 for PDF reopen/text/render validation.
- Kubo 0.43.1, commit acc53c093, repo version 18, Go 1.26.5.
- Kubo official Windows ZIP SHA-256:
  `c25871516dec4d97ce1d160a26c1e3fdad294cb0eea065c0c0343bcfca86c524`;
  verified against the GitHub release asset digest.
- Full package versions: `run-02/environment.json`. Download provenance/checksums
  are copied into `tool-provenance/`. No runtime binary or node repository is included.

## Fixture inventory and real Kubo CIDs

| Source file | Plain bytes | Cipher bytes | Validation after retrieve/decrypt | CID of ciphertext in run-02 |
|---|---:|---:|---|---|
| portrait.jpg | 7179 | 7207 | JPEG decode, 320 x 240; verified for Holder and Issuer | `QmYHAgN1uvzZRE4b6rZAhrsFkvnf5JZX2m7usDq25L63Kb` |
| diploma.pdf | 1838 | 1866 | One page, text extracted and rendered to PNG for both roles | `QmcjQe5hNyNXgWVfaWuwWqWVmrrPg74D1mo1CCSNmr85M6` |
| metadata.json | 150 | 178 | UTF-8 JSON parsed, expected synthetic fields checked for both roles | `QmZkC9WwSfZ583LSoA5n3J81HTyydw5yPBDDsuHaqaUa6e` |

PDF plaintext SHA-256 / docHash:
`299ee6afe8c116a97fa8bba33686c5002e564bf1295d44b48948d1785bbf7e12`.
It matched the reopened decrypted PDF for both Holder and Issuer. No value was
read from Ethereum; chain comparison remains an integration task.

All three downloaded ciphertexts matched upload bytes. Each was pinned (checked
using the real `/api/v0/pin/ls` endpoint), parsed and decrypted directly from the
HTTP result. Recovered files were written and reopened. Visual review of JPEG
and the recovered Holder PDF preview found no clipping or decoding issue.
Fixtures depict no real person and contain no name, student ID or other PII.

One 32-byte bundle AES key and three distinct 12-byte nonces were used. Holder
and Issuer had separate encrypted RSA-3072 PEMs in memory only; the two raw
wrapped keys were 384 bytes and independently restored the same AES key.

## Added security checks

15 extra pytest cases cover valid fixtures (3), modified nonce/ciphertext/tag (3),
wrong AES key, wrong AAD argument, changed AAD in both package and decrypt argument,
1000 nonce samples under one key/plaintext, both role unwrap plus cross-role
failure, wrong PEM password, modified RSA ciphertext, encrypted-PEM/fingerprint
consistency, and changed PDF hash. All passed in `run-02/all-unit.log`.

Sampling 1000 distinct nonces is an observation, not a proof of zero collision
probability. Core randomness remains unchanged. Old placeholder tests are retained
for regression; real-Kubo acceptance uses the new valid fixtures.

## Reproduce on a normal Windows workstation

From the repository root at the baseline with this additive M2 overlay:

```powershell
py -3.12 -m venv .venv-m2
.\.venv-m2\Scripts\python.exe -m pip install -r requirements-crypto-ipfs-m2.lock.txt
.\.venv-m2\Scripts\python.exe -u tests\manual\run_m2.py `
  --kubo-exe C:\tools\kubo\ipfs.exe `
  --kubo-repo C:\workspace\ssi-m2-private-node-NEW `
  --output evidence\m2\run-NEW
```

Use the official Kubo 0.43.1 executable. The repository path must not exist yet;
the output must be fresh so raw logs are never overwritten. `--port` defaults
to 15001 and must be unused. The runner initializes a dedicated test node, binds
only 127.0.0.1, disables swarm and gateway, and launches `daemon --offline`.
It does not touch an existing default IPFS repository or register Ethereum keys.
All actual argv/cwd/exit codes are in `commands.json`; environment and raw stdout/
stderr are separate. The embedded Python used for this run is an isolated portable
distribution, not a venv; the normal venv command above uses the same pinned set.

Core pipeline alone, with an already-running local node:

```powershell
python -u tests\manual\crypto_ipfs_m2.py --generate-fixtures
python -u tests\manual\crypto_ipfs_m2.py --api http://127.0.0.1:15001 --output evidence\m2\manual-real-kubo
```

Re-running encryption generates fresh AES/RSA keys/nonces, so ciphertexts and
CIDs normally change. Compare decrypted bytes/hashes to the fixtures, not to
the previous encrypted CID. Saved `.enc` files permit inspecting this run's
ciphertext bytes, but secret keys are intentionally absent, so the bundle does
not enable re-decryption of its archived `.enc` files. Re-run the script instead.

## Evidence contents

- `run-02/baseline-unit.log`, `all-unit.log`: unmodified pytest output.
- `run-02/fixture-generation.log`: generator stdout.
- `run-02/kubo-*.log`: version/init/config and original daemon stdout/stderr.
- `run-02/real-kubo.log`: original script stdout with real API version, CIDs,
  decode validations and final result. No hand-reconstructed terminal output.
- `run-02/real-kubo/result.json`: machine-readable summary plus hashes and CIDs.
- `run-02/real-kubo/holder/`, `issuer/`: reopened recovered synthetic files/previews.
- `run-01/`: preserved unsuccessful attempt, explicitly not Kubo PASS.
- Each run's `SHA256SUMS.json` protects its recorded evidence from accidental edits.
- `baseline-integrity.json`: byte comparison of all original 41 files against ZIP.

## API handoff / remaining dependencies

See `docs/2-planning-phase/crypto-ipfs-m2-api.md` for signatures, expected errors,
role key wrapping, direct retrieved-byte decrypt, hash comparison and consent boundary.
See `docs/2-planning-phase/rsa-backup-proposed.md` for backup/fingerprint preparation.

- DL-05 remains PROPOSED: public-key immutability/no rotation requires PM approval,
  A/B agreement and C/D review before any registration workflow is implemented.
- No contracts, ABI, dashboards, crypto core, Kubo client or FROZEN v1 edits.
- No Git commit or push. Changes are additive fixtures/tests/runner/docs/evidence.
- No chain consent grant/revoke, registry binding, EIP-191 signing, UI, Sepolia or
  cross-node/public-gateway availability was tested by M2.
- Local offline pin checks do not establish long-term availability, replication
  or persistence across restart. The daemon was stopped after the run.
- Known baseline Kubo client CID-validation/JSON-shape errors and suffix-only
  upload checks remain tracked; this milestone did not change their behavior.
- No private PEM, password, AES key or Ethereum wallet secret is saved in this
  evidence. The private Kubo repo contains a node identity and stays outside it.
- PM/D still need to review evidence and sign M2 acceptance; no self-approval.
