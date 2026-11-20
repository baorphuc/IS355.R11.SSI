# SSI MVP - M1 HARDENING CHECKPOINT
Date: 2026-11-18
Branch: feature/m1-contract-hardening

## 1. Implementation
- IdentitySBT: one-time Registry binding.
- IdentitySBT: prevent direct REGISTRY_ROLE assignment.
- IdentitySBT: Soulbound transfer protection.
- SSIRegistry: immutable RSA public key after registration.
- SSIRegistry: mint/revoke requires ISSUER_ROLE and original issuer.

## 2. Approved decisions
- DL-02: One DID can have multiple Credentials.
- DL-03: Only original issuer with ISSUER_ROLE can mint/revoke.
- DL-04: Registry binding is one-time.
- DL-05: RSA public key is immutable after registration.
- DL-01: At this 18/11 checkpoint, the working direction was to keep the SBT model and not add Marketplace/ERC20; it was not yet formal Project Owner approval.

## 3. Tests
- Hardhat: 6 passing.
- Python regression: 60 passed, 1 warning.
- git diff --check: clean.
- Soulbound mint, transfer rejection and burn tested.
- Dashboard integration: Holder -> Issuer -> SBT -> Consent -> Gated Service passed.

## 4. Deployment
- Hardhat local chainId: 31337.
- Registry, IdentitySBT and GatedService deployed and linked.
- Issuer role granted.
- GatedService deployment helper: scripts/deploy-gated-service.ts.

## 5. Modified files
- contracts/IdentitySBT.sol
- contracts/SSIRegistry.sol
- test/contracts.ts
- scripts/deploy-gated-service.ts

## 6. Pending work
- Clean-environment deployment verification.
- Review final M1 diff.
- Commit and push only after explicit approval.
- Create start-local.ps1 later, with fresh-chain and keep-chain modes.

## 7. Git status
- No commit created.
- No push performed.

## 8. Post-checkpoint note (documentation update, 2026-11-19)

This file preserves the 18/11 checkpoint and its original test counts. Subsequent
M1 work expanded the local test suite and clean-environment checks; it did not
retroactively change this snapshot. The current release-readiness reference is:

- Hardhat suite: 39 passing.
- Python unit: 66 passing; Python integration: 1 passing in the required local-node environment.
- Deployment workflow validates chain ID/signer, contract links/bytecode/roles and writes a non-overwriting manifest with deployment ID, transaction/block and genesis hashes.
- RSA role-key workflow uses RSA-3072, encrypted PKCS8 private PEM, SPKI fingerprint read-back and one-time on-chain registration.

No commit or push is implied by this note. Consult the current README, Decision Log
and M1 task evidence before accepting a release.

## 9. Post-checkpoint decision note (2026-11-19)

Project Owner approved DL-01 on 19/11/2026: `IdentitySBT.sol` (ERC-721/SBT) is
the selected NFT-contract path for rubric criterion 4; mint and token-gated
access are the two primary token operations, while revoke/burn is supporting
lifecycle behavior. ERC-20 and NFT Marketplace remain outside the MVP, and
FROZEN ABI v1 is unchanged. This is a scope decision only, not acceptance of
implementation, tests, local evidence or Sepolia deployment.
