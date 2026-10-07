import hashlib
import io
from pathlib import Path

import pytest

from scripts import fetch_raw_data


def test_fetch_downloads_only_after_hash_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_raw_data, "ROOT", tmp_path)
    payload = b"source data"
    row = {
        "dataset_id": "TEST",
        "relative_path": "data/raw/test.csv",
        "direct_download": "https://example.com/test.csv",
        "source_page": "https://example.com",
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    monkeypatch.setattr(fetch_raw_data.urllib.request, "urlopen", lambda *_args, **_kwargs: io.BytesIO(payload))

    path = fetch_raw_data.fetch(row)
    assert path.read_bytes() == payload
    assert fetch_raw_data.fetch(row) == path

    row["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        fetch_raw_data.fetch(row)
    assert path.read_bytes() == payload


def test_failed_download_does_not_leave_raw_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_raw_data, "ROOT", tmp_path)
    row = {
        "dataset_id": "TEST",
        "relative_path": "data/raw/test.csv",
        "direct_download": "https://example.com/test.csv",
        "source_page": "https://example.com",
        "sha256": "0" * 64,
    }
    monkeypatch.setattr(fetch_raw_data.urllib.request, "urlopen", lambda *_args, **_kwargs: io.BytesIO(b"bad"))

    with pytest.raises(ValueError, match="Downloaded SHA-256 mismatch"):
        fetch_raw_data.fetch(row)
    assert not (tmp_path / Path(row["relative_path"])).exists()
    assert not list((tmp_path / "data" / "raw").glob("*.part"))
