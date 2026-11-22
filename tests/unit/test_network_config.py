from unittest.mock import Mock

import pytest

from app import common
from web3_client.client import (
    NetworkConfigurationError,
    SSIClient,
    resolve_dashboard_network,
)


def test_dashboard_defaults_to_local_when_ssi_selection_is_absent():
    assert resolve_dashboard_network({"LOCAL_RPC_URL": "http://local-rpc"}) == (
        "http://local-rpc",
        31337,
    )


def test_dashboard_accepts_complete_sepolia_selection():
    assert resolve_dashboard_network(
        {
            "SSI_RPC_URL": "https://provider.example.invalid/token",
            "SSI_EXPECTED_CHAIN_ID": "11155111",
        }
    ) == ("https://provider.example.invalid/token", 11155111)


@pytest.mark.parametrize(
    "environment",
    [
        {"SSI_RPC_URL": "https://provider.example.invalid/token"},
        {"SSI_EXPECTED_CHAIN_ID": "11155111"},
        {"SSI_RPC_URL": "", "SSI_EXPECTED_CHAIN_ID": "11155111"},
        {"SSI_RPC_URL": "   ", "SSI_EXPECTED_CHAIN_ID": "11155111"},
    ],
)
def test_dashboard_rejects_partial_network_selection(environment):
    with pytest.raises(NetworkConfigurationError, match="có đủ"):
        resolve_dashboard_network(environment)


@pytest.mark.parametrize("chain", ["0", "-1", "11155111.0", "not-a-number"])
def test_dashboard_rejects_invalid_expected_chain(chain):
    with pytest.raises(NetworkConfigurationError, match="số nguyên dương"):
        resolve_dashboard_network(
            {"SSI_RPC_URL": "https://provider.example.invalid/token", "SSI_EXPECTED_CHAIN_ID": chain}
        )


def test_explicit_client_arguments_do_not_mix_with_dashboard_environment(monkeypatch):
    monkeypatch.setenv("SSI_RPC_URL", "https://provider.example.invalid/token")
    monkeypatch.delenv("SSI_EXPECTED_CHAIN_ID", raising=False)
    client = SSIClient("http://caller-rpc", 31337)
    assert client.rpc_url == "http://caller-rpc"
    assert client.expected_chain_id == 31337


def test_connection_mismatch_blocks_client():
    client = SSIClient.__new__(SSIClient)
    client.expected_chain_id = 11155111
    client.w3 = Mock()
    client.w3.is_connected.return_value = True
    client.w3.eth.chain_id = 31337
    with pytest.raises(ConnectionError, match="Sai Chain ID"):
        client.require_connection()


def test_connection_error_hides_rpc_token():
    client = SSIClient.__new__(SSIClient)
    client.rpc_url = "https://provider.example.invalid/secret-token"
    client.expected_chain_id = 11155111
    client.w3 = Mock()
    client.w3.is_connected.return_value = False
    with pytest.raises(ConnectionError) as error:
        client.require_connection()
    assert "secret-token" not in str(error.value)


@pytest.mark.parametrize("stage", ["connected", "chain_id"])
def test_provider_exception_hides_rpc_token_and_traceback(stage):
    client = SSIClient.__new__(SSIClient)
    client.expected_chain_id = 11155111
    client.w3 = Mock()
    token = "provider-secret-token"
    if stage == "connected":
        client.w3.is_connected.side_effect = RuntimeError(f"https://rpc.invalid/{token}")
    else:
        client.w3.is_connected.return_value = True
        type(client.w3.eth).chain_id = property(
            lambda _self: (_ for _ in ()).throw(RuntimeError(f"https://rpc.invalid/{token}"))
        )

    with pytest.raises(ConnectionError) as error:
        client.require_connection()
    assert token not in str(error.value)
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__ is True


def test_successful_connection_returns_and_remembers_verified_chain():
    client = SSIClient.__new__(SSIClient)
    client.expected_chain_id = 11155111
    client.verified_chain_id = None
    client.w3 = Mock()
    client.w3.is_connected.return_value = True
    client.w3.eth.chain_id = 11155111
    assert client.require_connection() == 11155111
    assert client.verified_chain_id == 11155111


class DashboardStopped(Exception):
    pass


def test_page_header_uses_verified_chain_without_second_rpc_read(monkeypatch):
    class VerifiedClient:
        def require_connection(self):
            return 11155111

        @property
        def w3(self):
            raise AssertionError("page_header must not read chain ID a second time")

    client = VerifiedClient()
    fake_streamlit = Mock()
    monkeypatch.setattr(common, "load_dotenv", Mock())
    monkeypatch.setattr(common, "SSIClient", lambda: client)
    monkeypatch.setattr(common, "st", fake_streamlit)

    assert common.page_header("Verifier") is client
    fake_streamlit.success.assert_called_once_with("RPC đã kết nối · chainId 11155111")


def test_page_header_stops_before_dashboard_business_logic_on_connection_error(monkeypatch):
    client = Mock()
    client.require_connection.side_effect = ConnectionError("Lỗi kết nối an toàn")
    fake_streamlit = Mock()
    fake_streamlit.stop.side_effect = DashboardStopped()
    monkeypatch.setattr(common, "load_dotenv", Mock())
    monkeypatch.setattr(common, "SSIClient", lambda: client)
    monkeypatch.setattr(common, "st", fake_streamlit)

    with pytest.raises(DashboardStopped):
        common.page_header("Holder")
    fake_streamlit.success.assert_not_called()
