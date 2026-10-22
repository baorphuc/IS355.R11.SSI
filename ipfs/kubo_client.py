from pathlib import Path
import requests


class KuboClient:
    def __init__(self, api_url: str = "http://127.0.0.1:5001", timeout: int = 30):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def add_encrypted(self, path: Path) -> str:
        if path.suffix != ".enc":
            raise ValueError("Chỉ upload file đã mã hóa có đuôi .enc")
        with path.open("rb") as stream:
            response = requests.post(
                f"{self.api_url}/api/v0/add?pin=true",
                files={"file": (path.name, stream, "application/octet-stream")},
                timeout=self.timeout,
            )
        response.raise_for_status()
        return response.json()["Hash"]

    def cat(self, cid: str) -> bytes:
        response = requests.post(f"{self.api_url}/api/v0/cat", params={"arg": cid}, timeout=self.timeout)
        response.raise_for_status()
        return response.content
