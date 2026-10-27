"""Fixture dùng chung cho test IPFS Kubo (giả Kubo qua session.mock)."""

from unittest.mock import MagicMock

import hashlib
import pytest
import requests

from ipfs.kubo_client import KuboClient

API = "http://127.0.0.1:5001"


@pytest.fixture
def fake_kubo():
    """Trả về (KuboClient, store) mô phỏng Kubo add/cat trong bộ nhớ.

    CID là nội dung địa chỉ (content-addressed) như Kubo thật, nên mỗi upload
    nội dung khác nhau nhận CID khác nhau. Không cần dịch vụ Kubo thật.
    """
    store: dict[str, bytes] = {}

    def fake_post(url, **kwargs):
        path = url.replace(API, "")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if path == "/api/v0/add?pin=true":
            file_tuple = kwargs["files"]["file"]
            _name, stream, _ctype = file_tuple
            data = stream.read() if hasattr(stream, "read") else bytes(stream)
            cid = "Qm" + hashlib.sha256(data).hexdigest()[:44]
            store[cid] = data
            resp.json = MagicMock(return_value={"Hash": cid, "Name": _name})
            return resp
        if path == "/api/v0/cat":
            cid = kwargs["params"]["arg"]
            if cid not in store:
                resp.raise_for_status = MagicMock(side_effect=requests.HTTPError("404 Not Found"))
                resp.status_code = 404
                return resp
            resp.content = store[cid]
            return resp
        resp.raise_for_status = MagicMock(side_effect=requests.HTTPError("404"))
        resp.status_code = 404
        return resp

    session = MagicMock(spec=requests.Session)
    session.post = fake_post
    client = KuboClient(api_url=API, session=session)
    return client, store
