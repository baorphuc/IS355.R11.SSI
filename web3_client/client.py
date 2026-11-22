from web3.logs import DISCARD
import json
import os
from pathlib import Path
from typing import Any

from eth_account import Account
from web3 import Web3
from web3.exceptions import TimeExhausted


class NetworkConfigurationError(ConnectionError):
    """Raised when the dashboard network selection is incomplete or unsafe."""


def resolve_dashboard_network(environ: dict[str, str] | None = None) -> tuple[str, int]:
    """Resolve the no-argument dashboard configuration.

    ``SSI_RPC_URL`` and ``SSI_EXPECTED_CHAIN_ID`` form one atomic selection.
    Supplying only one of them is rejected instead of falling back to local.
    When neither is present, the historical local workflow remains explicit:
    ``LOCAL_RPC_URL`` (or localhost) on chain 31337.
    """
    env = os.environ if environ is None else environ
    selected_rpc = env.get("SSI_RPC_URL")
    selected_chain = env.get("SSI_EXPECTED_CHAIN_ID")

    if selected_rpc is None and selected_chain is None:
        return env.get("LOCAL_RPC_URL", "http://127.0.0.1:8545"), 31337

    selected_rpc = (selected_rpc or "").strip()
    selected_chain = (selected_chain or "").strip()
    if not selected_rpc or not selected_chain:
        raise NetworkConfigurationError(
            "Cấu hình mạng SSI phải có đủ SSI_RPC_URL và SSI_EXPECTED_CHAIN_ID."
        )

    try:
        expected_chain_id = int(selected_chain, 10)
    except ValueError as exc:
        raise NetworkConfigurationError("SSI_EXPECTED_CHAIN_ID phải là số nguyên dương.") from exc
    if expected_chain_id <= 0 or str(expected_chain_id) != selected_chain:
        raise NetworkConfigurationError("SSI_EXPECTED_CHAIN_ID phải là số nguyên dương.")
    return selected_rpc, expected_chain_id


class SSIClient:
    def __init__(
        self,
        rpc_url: str | None = None,
        expected_chain_id: int | None = None,
        timeout: int = 30,
    ):
        # Explicit arguments preserve the existing caller contract and do not
        # combine with dashboard environment selection.
        if rpc_url is None and expected_chain_id is None:
            self.rpc_url, self.expected_chain_id = resolve_dashboard_network()
        else:
            self.rpc_url = rpc_url or os.getenv("LOCAL_RPC_URL", "http://127.0.0.1:8545")
            self.expected_chain_id = expected_chain_id

        self.w3 = Web3(
            Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": timeout})
        )
        self.verified_chain_id: int | None = None

    def require_connection(self) -> int:
        try:
            connected = self.w3.is_connected()
            actual_chain_id = self.w3.eth.chain_id if connected else None
        except Exception:
            # Provider exceptions can include authenticated URLs. Never expose
            # their text through the dashboard's connection error path.
            raise ConnectionError("Không kết nối được Ethereum RPC đã cấu hình.") from None

        if not connected:
            # Do not disclose a provider URL, which may embed an API token.
            raise ConnectionError("Không kết nối được Ethereum RPC đã cấu hình.")

        if (
            self.expected_chain_id is not None
            and actual_chain_id != self.expected_chain_id
        ):
            raise ConnectionError(
                f"Sai Chain ID: mong đợi {self.expected_chain_id}, "
                f"nhận được {actual_chain_id}"
            )
        self.verified_chain_id = actual_chain_id
        return actual_chain_id

    @staticmethod
    def load_abi(artifact_path: Path) -> list[dict[str, Any]]:
        artifact = json.loads(
            artifact_path.read_text(encoding="utf-8")
        )

        if "abi" not in artifact:
            raise ValueError(f"Artifact không chứa ABI: {artifact_path}")

        return artifact["abi"]

    def contract(
        self,
        address: str,
        abi: list[dict[str, Any]],
        require_code: bool = True,
    ):
        checksum_address = Web3.to_checksum_address(address)

        if require_code:
            code = self.w3.eth.get_code(checksum_address)

            if not code:
                raise ValueError(
                    f"Không tìm thấy bytecode tại contract {checksum_address}"
                )

        return self.w3.eth.contract(
            address=checksum_address,
            abi=abi,
        )

    def load_contract(
        self,
        address: str,
        artifact_path: Path,
    ):
        abi = self.load_abi(artifact_path)
        return self.contract(address, abi)


    def _validate_credential_id(self, credential_id: int) -> int:
        """Kiểm tra Credential ID hợp lệ."""
        credential_id = int(credential_id)
        if credential_id < 0:
            raise ValueError("Credential ID không được âm")
        return credential_id

    def get_credential(self, registry, credential_id: int):
        """Đọc thông tin credential từ SSIRegistry."""
        self.require_connection()
        credential_id = self._validate_credential_id(credential_id)
        return registry.functions.getCredential(credential_id).call()

    def verify_credential(self, registry, credential_id: int):
        """Kiểm tra trạng thái và thông tin xác minh credential."""
        self.require_connection()
        credential_id = self._validate_credential_id(credential_id)
        return registry.functions.verifyCredential(credential_id).call()

    def has_access(self, registry, credential_id: int, verifier_address: str) -> bool:
        """Kiểm tra Verifier có quyền truy cập credential hay không."""
        self.require_connection()
        credential_id = self._validate_credential_id(credential_id)
        verifier_address = self.w3.to_checksum_address(verifier_address)

        return registry.functions.hasAccess(
            credential_id, verifier_address
        ).call()

    def get_consent(self, registry, credential_id: int, verifier_address: str):
        """Đọc trạng thái consent và wrapped key dành cho Verifier."""
        self.require_connection()
        credential_id = self._validate_credential_id(credential_id)
        verifier_address = self.w3.to_checksum_address(verifier_address)

        return registry.functions.getConsent(
            credential_id, verifier_address
        ).call()

    def get_identity_sbt(self, registry) -> str:
        """Lấy địa chỉ IdentitySBT đang liên kết với Registry."""
        self.require_connection()
        return registry.functions.identitySBT().call()


    def create_did(self, registry, did: str, private_key: str):
        """Holder đăng ký DID lên SSIRegistry."""
        self.require_connection()

        if not isinstance(did, str) or not did.strip():
            raise ValueError("DID không được để trống")

        account = Account.from_key(private_key)
        identity = registry.functions.identities(account.address).call()

        if identity[0]:
            raise ValueError("Holder đã đăng ký DID")

        receipt = self.send_transaction(
            registry.functions.createDID(did.strip()),
            private_key,
        )

        events = registry.events.DIDCreated().process_receipt(
            receipt, errors=DISCARD
        )

        if not events:
            raise RuntimeError("Giao dịch thành công nhưng không tìm thấy DIDCreated")

        event = events[0]["args"]

        return {
            "holder": event["holder"],
            "did": event["did"],
            "tx_hash": receipt["transactionHash"].hex(),
            "block_number": receipt["blockNumber"],
        }

    def request_credential(
        self,
        registry,
        portrait_cid: str,
        diploma_cid: str,
        metadata_cid: str,
        wrapped_key_for_holder: bytes,
        wrapped_key_for_issuer: bytes,
        private_key: str,
    ):
        """Holder gửi yêu cầu cấp Credential lên SSIRegistry."""
        self.require_connection()

        # Kiểm tra Holder đã đăng ký DID chưa.
        account = Account.from_key(private_key)
        identity = registry.functions.identities(account.address).call()

        if not identity[0]:
            raise ValueError("Holder chưa đăng ký DID")

        # Kiểm tra ba CID.
        cids = {
            "portrait_cid": portrait_cid,
            "diploma_cid": diploma_cid,
            "metadata_cid": metadata_cid,
        }

        for name, cid in cids.items():
            if not isinstance(cid, str) or not cid.strip():
                raise ValueError(f"{name} không hợp lệ")

        # RSA-3072 tạo ciphertext RSA có kích thước 384 bytes.
        for name, wrapped_key in {
            "wrapped_key_for_holder": wrapped_key_for_holder,
            "wrapped_key_for_issuer": wrapped_key_for_issuer,
        }.items():
            if not isinstance(wrapped_key, bytes) or len(wrapped_key) != 384:
                raise ValueError(
                    f"{name} phải là raw RSA-3072 ciphertext 384 bytes"
                )

        receipt = self.send_transaction(
            registry.functions.requestCredential(
                portrait_cid.strip(),
                diploma_cid.strip(),
                metadata_cid.strip(),
                wrapped_key_for_holder,
                wrapped_key_for_issuer,
            ),
            private_key,
        )

        events = registry.events.CredentialRequested().process_receipt(
            receipt, errors=DISCARD
        )

        if not events:
            raise RuntimeError(
                "Giao dịch thành công nhưng không tìm thấy CredentialRequested"
            )

        event = events[0]["args"]

        return {
            "credential_id": int(event["credentialId"]),
            "holder": event["holder"],
            "tx_hash": receipt["transactionHash"].hex(),
            "block_number": receipt["blockNumber"],
        }

    def revoke_credential(
        self,
        registry,
        credential_id: int,
        private_key: str,
    ) -> dict[str, Any]:
        """Issuer thu hồi Credential đã phát hành."""

        self.require_connection()

        credential_id = self._validate_credential_id(credential_id)

        account = Account.from_key(private_key)

        credential = self.get_credential(
             registry,
             credential_id,
        )

        status = int(credential[9])
        issuer = credential[1]

        if status != 2:
            raise ValueError(
                "Chỉ Credential đang ISSUED mới được thu hồi"
            )

        if issuer.lower() != account.address.lower():
            raise PermissionError(
                "Chỉ Issuer đã phát hành Credential mới được thu hồi"
            )

        receipt = self.send_transaction(
            registry.functions.revokeCredential(credential_id),
            private_key,
        )

        events = registry.events.CredentialRevoked().process_receipt(
            receipt,
            errors=DISCARD,
        )

        if not events:
            raise RuntimeError(
                "Giao dịch thành công nhưng không tìm thấy CredentialRevoked"
            )

        return {
            "credential_id": credential_id,
            "issuer": account.address,
            "tx_hash": receipt["transactionHash"].hex(),
            "block_number": receipt["blockNumber"],
        }

    def access_service(
        self,
        gated_service,
        credential_id: int,
        private_key: str,
    ) -> dict[str, Any]:
        """Holder sử dụng SBT và Credential hợp lệ để truy cập dịch vụ."""
        self.require_connection()
        credential_id = self._validate_credential_id(credential_id)

        account = Account.from_key(private_key)

        # Kiểm tra Holder hiện đang sở hữu SBT.
        sbt_address = gated_service.functions.sbt().call()
        sbt_abi_path = (
            Path(__file__).resolve().parents[1]
            / "artifacts/contracts/IdentitySBT.sol/IdentitySBT.json"
        )
        sbt = self.load_contract(sbt_address, sbt_abi_path)

        owner = sbt.functions.ownerOf(credential_id).call()

        if owner.lower() != account.address.lower():
            raise PermissionError(
                "Tài khoản gọi không sở hữu SBT của Credential này."
            )

        # Kiểm tra Credential còn hợp lệ trước khi gửi transaction.
        registry_address = gated_service.functions.registry().call()
        registry_abi_path = (
            Path(__file__).resolve().parents[1]
            / "artifacts/contracts/SSIRegistry.sol/SSIRegistry.json"
        )
        registry = self.load_contract(
            registry_address, registry_abi_path
        )

        verification = self.verify_credential(
            registry, credential_id
        )

        if not bool(verification[0]) or int(verification[3]) != 2:
            raise ValueError(
                "Credential không hợp lệ hoặc đã bị thu hồi."
            )

        if verification[1].lower() != account.address.lower():
            raise PermissionError(
                "Holder của Credential không khớp tài khoản gọi."
            )

        # Gọi accessService bằng tài khoản Holder.
        function_call = gated_service.functions.accessService(
            credential_id
        )

        receipt = self.send_transaction(
            function_call,
            private_key,
        )

        events = gated_service.events.ServiceAccessed().process_receipt(
            receipt,
            errors=DISCARD,
        )

        if not events:
            raise RuntimeError(
                "Giao dịch thành công nhưng không tìm thấy ServiceAccessed."
            )

        return {
            "credential_id": credential_id,
            "holder": account.address,
            "tx_hash": receipt["transactionHash"].hex(),
            "block_number": receipt["blockNumber"],
        }

    def send_transaction(
        self,
        function_call: Any,
        private_key: str,
        timeout: int = 120,
    ) -> dict[str, Any]:
        self.require_connection()

        account = Account.from_key(private_key)

        if self.w3.eth.chain_id != self.expected_chain_id and (
            self.expected_chain_id is not None
        ):
            raise ConnectionError("Chain ID không khớp cấu hình")

        balance = self.w3.eth.get_balance(account.address)

        if balance == 0:
            raise ValueError(
                f"Tài khoản {account.address} không có ETH để trả gas"
            )

        tx = function_call.build_transaction({
            "from": account.address,
            "nonce": self.w3.eth.get_transaction_count(
                account.address, "pending"
            ),
            "chainId": self.w3.eth.chain_id,
        })

        tx["gas"] = self.w3.eth.estimate_gas(tx)
        tx["maxPriorityFeePerGas"] = self.w3.to_wei(1, "gwei")
        tx["maxFeePerGas"] = (
            self.w3.eth.gas_price * 2 + tx["maxPriorityFeePerGas"]
        )

        signed = account.sign_transaction(tx)

        tx_hash = self.w3.eth.send_raw_transaction(
            signed.raw_transaction
        )

        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=timeout,
            )
        except TimeExhausted as exc:
            raise TimeoutError(
                f"Transaction chưa được xác nhận sau {timeout} giây: "
                f"{tx_hash.hex()}"
            ) from exc

        result = dict(receipt)

        if receipt["status"] != 1:
            raise RuntimeError(
                f"Transaction thất bại: {tx_hash.hex()}"
            )

        return result
