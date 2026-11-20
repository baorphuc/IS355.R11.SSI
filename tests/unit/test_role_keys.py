from unittest.mock import Mock
import pytest
from eth_account import Account

from crypto.role_keys import create_pair, fingerprint, load_pair, paths
from web3_client.role_keys import register_pair, verify_public


@pytest.fixture
def pair(tmp_path):
    digest = create_pair(tmp_path, "holder", "temporary-password")
    private, public = load_pair(tmp_path, "holder", "temporary-password")
    return private, public, digest


def test_create_and_fingerprint(tmp_path, pair):
    private, pem, digest = pair
    assert b"ENCRYPTED PRIVATE KEY" in private
    assert digest == fingerprint(pem.replace(b"\n", b"\r\n"))
    assert digest == fingerprint(paths(tmp_path, "holder")[1].read_bytes())


def test_duplicate_preserves_pair(tmp_path, pair):
    with pytest.raises(FileExistsError, match="already exists"):
        create_pair(tmp_path, "holder", "other")
    assert tuple(p.read_bytes() for p in paths(tmp_path, "holder")) == pair[:2]


@pytest.mark.parametrize("index", [0, 1])
def test_incomplete_never_replaced(tmp_path, index):
    survivor = paths(tmp_path, "holder")[index]
    survivor.write_bytes(b"sentinel")
    with pytest.raises(FileExistsError, match="Incomplete"):
        create_pair(tmp_path, "holder", "temporary")
    assert survivor.read_bytes() == b"sentinel"
    with pytest.raises(FileNotFoundError):
        load_pair(tmp_path, "holder", "temporary")


def test_no_automatic_creation(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_pair(tmp_path, "issuer", "temporary")
    assert not list(tmp_path.iterdir())


def test_registration_roundtrip(tmp_path, pair, capsys, caplog):
    signer = Account.create()
    registry, client = Mock(), Mock()
    read = registry.functions.identities.return_value.call
    read.side_effect = [(False, "", data) for data in (b"", pair[1], pair[1], pair[1])]
    for _ in range(2):
        assert register_pair(client, registry, signer.address, signer.key, tmp_path, "holder", "temporary-password") == pair[2]
    registry.functions.registerKey.assert_called_once_with(pair[1])
    client.send_transaction.assert_called_once()
    assert all(call.args == (signer.address,) for call in registry.functions.identities.call_args_list)
    out, err = capsys.readouterr()
    for secret in ("PRIVATE KEY", signer.key.hex(), "temporary-password", pair[0].decode().splitlines()[1]):
        assert secret not in out + err + caplog.text


def test_mismatch_and_missing_registration(tmp_path, pair):
    signer = Account.create()
    registry, client = Mock(), Mock()
    read = registry.functions.identities.return_value.call
    read.return_value = (False, "", b"")
    with pytest.raises(ValueError, match="not registered"):
        verify_public(registry, signer.address, pair[1])
    create_pair(tmp_path, "verifier", "temporary")
    other = paths(tmp_path, "verifier")[1].read_bytes()
    read.return_value = (False, "", other)
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        register_pair(client, registry, signer.address, signer.key, tmp_path, "holder", "temporary-password")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        verify_public(registry, signer.address, pair[1])
    with pytest.raises(ValueError, match="Signer"):
        register_pair(client, registry, Account.create().address, signer.key, tmp_path, "holder", "temporary-password")
    client.send_transaction.assert_not_called()
    paths(tmp_path, "holder")[1].write_bytes(other)
    with pytest.raises(ValueError, match="pair mismatch"):
        load_pair(tmp_path, "holder", "temporary-password")
