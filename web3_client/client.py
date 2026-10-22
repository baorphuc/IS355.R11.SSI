import json
import os
from pathlib import Path
from typing import Any

from eth_account import Account
from web3 import Web3


class SSIClient:
    def __init__(self, rpc_url: str | None = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url or os.getenv("LOCAL_RPC_URL", "http://127.0.0.1:8545")))

    def require_connection(self) -> None:
        if not self.w3.is_connected():
            raise ConnectionError("Không kết nối được Ethereum RPC")

    @staticmethod
    def load_abi(artifact_path: Path) -> list[dict[str, Any]]:
        return json.loads(artifact_path.read_text(encoding="utf-8"))["abi"]

    def contract(self, address: str, abi: list[dict[str, Any]]):
        return self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)

    def send_transaction(self, function_call: Any, private_key: str) -> dict[str, Any]:
        account = Account.from_key(private_key)
        tx = function_call.build_transaction({
            "from": account.address,
            "nonce": self.w3.eth.get_transaction_count(account.address),
            "chainId": self.w3.eth.chain_id,
        })
        tx["gas"] = self.w3.eth.estimate_gas(tx)
        tx["maxPriorityFeePerGas"] = self.w3.to_wei(1, "gwei")
        tx["maxFeePerGas"] = self.w3.eth.gas_price * 2 + tx["maxPriorityFeePerGas"]
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return dict(self.w3.eth.wait_for_transaction_receipt(tx_hash))


# TODO(C): thêm wrapper có kiểu cho từng hàm contract sau khi ABI được đóng băng.
