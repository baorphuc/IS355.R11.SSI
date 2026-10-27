"""Test IPFS Kubo client với các giả mô phỏng (không cần dịch vụ Kubo thật)."""

from unittest.mock import MagicMock

import pytest
import requests

from ipfs.kubo_client import (
    InvalidCIDError,
    KuboConnectionError,
    KuboResponseError,
    KuboClient,
)

API = "http://127.0.0.1:5001"
VALID_CID = "Qm" + "x" * 44  # dạng CIDv0 giả hợp lệ


def _client_with_post(fake_post):
    session = MagicMock(spec=requests.Session)
    session.post = fake_post
    return KuboClient(api_url=API, session=session)


def test_upload_and_retrieve_preserve_bytes(fake_kubo):
    client, store = fake_kubo
    original = bytes(range(256)) * 20  # 5120 byte giả ciphertext
    cid = client.add_bytes(original, "diploma.pdf.enc")
    assert cid in store
    retrieved = client.cat(cid)
    assert retrieved == original


def test_add_encrypted_preserve_bytes(tmp_path, fake_kubo):
    client, _ = fake_kubo
    enc_path = tmp_path / "portrait.jpg.enc"
    original = b"\x89PNG encrypted payload bytes"
    enc_path.write_bytes(original)
    cid = client.add_encrypted(enc_path)
    assert client.cat(cid) == original


def test_add_bytes_rejects_non_enc_filename(fake_kubo):
    client, _ = fake_kubo
    with pytest.raises(ValueError):
        client.add_bytes(b"data", "diploma.pdf")


def test_add_encrypted_rejects_non_enc_path(tmp_path, fake_kubo):
    client, _ = fake_kubo
    bad = tmp_path / "notes.txt"
    bad.write_bytes(b"not encrypted")
    with pytest.raises(ValueError):
        client.add_encrypted(bad)


def test_add_bytes_rejects_empty_data(fake_kubo):
    client, _ = fake_kubo
    with pytest.raises(ValueError):
        client.add_bytes(b"", "empty.enc")


def test_invalid_cid_rejected(fake_kubo):
    client, _ = fake_kubo
    with pytest.raises(InvalidCIDError):
        client.cat("not-a-real-cid!")
    with pytest.raises(InvalidCIDError):
        client.cat("")
    with pytest.raises(InvalidCIDError):
        client.cat("Qm" + "x" * 10)  # CIDv0 bắt đầu Qm nhưng sai độ dài (46)


def test_cid_without_special_chars_only(fake_kubo):
    client, _ = fake_kubo
    with pytest.raises(InvalidCIDError):
        client.cat("Qm!!!invalid!!!cid")


def test_connection_error_unreachable_kubo():
    def boom(url, **kwargs):
        raise requests.exceptions.ConnectionError("connection refused")

    client = _client_with_post(boom)
    with pytest.raises(KuboConnectionError):
        client.cat(VALID_CID)


def test_timeout_kubo():
    def boom(url, **kwargs):
        raise requests.exceptions.Timeout("timed out")

    client = _client_with_post(boom)
    with pytest.raises(KuboConnectionError):
        client.cat(VALID_CID)


def test_http_error_missing_cid(fake_kubo):
    client, _ = fake_kubo
    # CID hợp lệ nhưng Kubo chưa có → 404
    with pytest.raises(KuboResponseError):
        client.cat(VALID_CID)


def test_http_error_bad_response():
    def bad_json(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"error": "no hash"})
        return resp

    client = _client_with_post(bad_json)
    with pytest.raises(KuboResponseError):
        client.add_bytes(b"data", "file.enc")


def test_empty_cat_content_rejected():
    def empty(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.content = b""
        return resp

    client = _client_with_post(empty)
    with pytest.raises(KuboResponseError):
        client.cat(VALID_CID)


def test_add_returns_validated_cid(fake_kubo):
    client, store = fake_kubo
    cid = client.add_bytes(b"data", "a.enc")
    # CID phải qua validation của KuboClient và lưu trong store
    KuboClient.validate_cid(cid)
    assert cid in store
    assert client.cat(cid) == b"data"
