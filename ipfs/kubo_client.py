from pathlib import Path
import io
import re
import requests


class KuboError(Exception):
    """Lỗi cơ bản khi làm việc với Kubo IPFS."""


class KuboConnectionError(KuboError):
    """Không kết nối hoặc hết thời gian chờ khi gọi Kubo."""


class KuboResponseError(KuboError):
    """Kubo phản hồi không thành công, thiếu CID hoặc nội dung trả về trống."""


class InvalidCIDError(KuboError):
    """CID không đúng định dạng."""


_CID_RE = re.compile(r"^[A-Za-z0-9]+$")
_MIN_CID_LEN = 8
_MAX_CID_LEN = 128


class KuboClient:
    """Client HTTP tối giản cho IPFS Kubo (API /api/v0).

    Chỉ upload/tải file đã mã hóa (.enc). Không xử lý khóa riêng hoặc dữ liệu thô.
    """

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:5001",
        timeout: int = 30,
        session: requests.Session | None = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

    def _post(self, path: str, **kwargs) -> requests.Response:
        """Gửi POST đến Kubo và chuyển đổi lỗi HTTP/mạng thành exceptions rõ ràng."""
        try:
            response = self._session.post(
                f"{self.api_url}{path}", timeout=self.timeout, **kwargs
            )
        except requests.exceptions.Timeout as exc:
            raise KuboConnectionError(f"Yêu cầu Kubo hết thời gian chờ ({self.timeout}s)") from exc
        except requests.exceptions.ConnectionError as exc:
            raise KuboConnectionError(f"Không kết nối được Kubo tại {self.api_url}") from exc
        except requests.exceptions.RequestException as exc:
            raise KuboConnectionError(f"Yêu cầu Kubo thất bại: {type(exc).__name__}") from exc
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise KuboResponseError(f"Kubo {path} trả về HTTP {response.status_code}") from exc
        return response

    @staticmethod
    def validate_cid(cid: str) -> None:
        """Kiểm tra CID có dạng base58/base32 hợp lệ (không lộ dữ liệu nhạy cảm)."""
        if (
            not isinstance(cid, str)
            or not _CID_RE.match(cid)
            or not (_MIN_CID_LEN <= len(cid) <= _MAX_CID_LEN)
        ):
            raise InvalidCIDError(
                "CID không hợp lệ: phải là chuỗi base58/base32 không chứa ký tự đặc biệt"
            )
        if cid.startswith("Qm") and len(cid) != 46:
            raise InvalidCIDError(
                "CIDv0 không hợp lệ: dự kiến 46 ký tự base58 bắt đầu bằng Qm"
            )

    def add_bytes(self, data: bytes, filename: str) -> str:
        """Upload bytes đã mã hóa lên Kubo (pin=true) và trả về CID.

        `filename` phải có đuôi `.enc` để đảm bảo không vô tình upload dữ liệu thô.
        """
        if not filename.endswith(".enc"):
            raise ValueError("Chỉ upload file đã mã hóa có đuôi .enc")
        if not data:
            raise ValueError("Không upload dữ liệu rỗng")
        response = self._post(
            "/api/v0/add?pin=true",
            files={"file": (filename, io.BytesIO(data), "application/octet-stream")},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise KuboResponseError("Phản hồi Kubo add không phải JSON hợp lệ") from exc
        cid = payload.get("Hash")
        if not cid:
            raise KuboResponseError("Phản hồi Kubo add thiếu trường CID (Hash)")
        self.validate_cid(str(cid))
        return str(cid)

    def add_encrypted(self, path: Path) -> str:
        """Upload file đã mã hóa (.enc) lên Kubo và trả về CID."""
        if path.suffix != ".enc":
            raise ValueError("Chỉ upload file đã mã hóa có đuôi .enc")
        with path.open("rb") as stream:
            return self.add_bytes(stream.read(), path.name)

    def cat(self, cid: str) -> bytes:
        """Tải nội dung file theo CID từ Kubo; lỗi nếu CID sai hoặc nội dung trống."""
        self.validate_cid(cid)
        response = self._post("/api/v0/cat", params={"arg": cid})
        if not response.content:
            raise KuboResponseError("Kubo cat trả về nội dung trống cho CID")
        return response.content
