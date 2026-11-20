from eth_account import Account
from web3 import Web3

from crypto.role_keys import fingerprint, load_pair


def registered(registry, wallet):
    return bytes(registry.functions.identities(Web3.to_checksum_address(wallet)).call()[2])


def verify_public(registry, wallet, pem):
    stored = registered(registry, wallet)
    if not stored:
        raise ValueError("RSA key is not registered")
    if fingerprint(stored) != fingerprint(pem):
        raise ValueError("Registered RSA fingerprint mismatch")
    return pem


def register_pair(client, registry, wallet, signer, directory, role, password, expected_fingerprint=None):
    if Account.from_key(signer).address != Web3.to_checksum_address(wallet):
        raise ValueError("Signer does not match role wallet")
    _, pem = load_pair(directory, role, password)
    if expected_fingerprint is not None and fingerprint(pem) != expected_fingerprint:
        raise ValueError("PEM changed after backup confirmation")
    if not registered(registry, wallet):
        client.send_transaction(registry.functions.registerKey(pem), signer)
    verify_public(registry, wallet, pem)
    return fingerprint(pem)


def verified_pair(registry, wallet, directory, role, password):
    secret, public = load_pair(directory, role, password)
    verify_public(registry, wallet, public)
    return secret, public
