"""Integration smoke test. Chạy sau `npm run compile` và khi `npm run node` đang mở."""
import json
import os
from pathlib import Path

import pytest
from eth_account.messages import encode_defunct
from web3 import Web3


ROOT = Path(__file__).resolve().parents[2]
RPC = os.getenv("LOCAL_RPC_URL", "http://127.0.0.1:8545")


def artifact(contract: str) -> dict:
    path = ROOT / "artifacts" / "contracts" / f"{contract}.sol" / f"{contract}.json"
    if not path.exists():
        pytest.skip("Chưa compile contract: chạy npm run compile")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def w3():
    client = Web3(Web3.HTTPProvider(RPC))
    if not client.is_connected():
        pytest.skip("Hardhat node chưa chạy: mở terminal khác và chạy npm run node")
    return client


def deploy(w3: Web3, name: str, args: tuple = ()):
    data = artifact(name)
    factory = w3.eth.contract(abi=data["abi"], bytecode=data["bytecode"])
    tx_hash = factory.constructor(*args).transact({"from": w3.eth.accounts[0]})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return w3.eth.contract(address=receipt.contractAddress, abi=data["abi"])


def test_web3_lifecycle_on_hardhat(w3: Web3):
    admin, holder, issuer = w3.eth.accounts[:3]
    sbt = deploy(w3, "IdentitySBT", (admin,))
    registry = deploy(w3, "SSIRegistry", (admin, sbt.address))
    gate = deploy(w3, "GatedService", (sbt.address, registry.address))
    sbt.functions.setRegistry(registry.address).transact({"from": admin})
    role = registry.functions.ISSUER_ROLE().call()
    registry.functions.grantRole(role, issuer).transact({"from": admin})

    registry.functions.createDID("did:ssi:holder").transact({"from": holder})
    registry.functions.requestCredential("jpg", "pdf", "json", b"holder", b"issuer").transact({"from": holder})
    doc_hash = Web3.keccak(text="fake diploma")
    digest = registry.functions.signingDigest(1, doc_hash).call()
    private_key = w3.provider.make_request("eth_accounts", [])["result"]  # proves RPC path; key is intentionally not exposed
    assert issuer.lower() in [value.lower() for value in private_key]

    # Hardhat cho phép eth_sign; Solidity kiểm tra EIP-191 tương ứng.
    signature = w3.eth.sign(issuer, hexstr=digest.hex())
    registry.functions.issueCredential(1, doc_hash, signature).transact({"from": issuer})
    registry.functions.mintSBT(1).transact({"from": issuer})
    receipt = w3.eth.wait_for_transaction_receipt(gate.functions.accessService(1).transact({"from": holder}))
    assert len(gate.events.ServiceAccessed().process_receipt(receipt)) == 1
    assert registry.functions.verifyCredential(1).call()[0] is True
