import pytest
from json import JSONDecodeError
from pathlib import Path
from client_erp_adapter import ClientERP

client_erp = ClientERP()


def test_read_api_response_no_permission(monkeypatch):
    def fake_open(self, *args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "open", fake_open)
    result = client_erp.read_json_file(Path("nopermission.json"))
    assert result is None


def test_read_api_response_malformed_json(monkeypatch):
    class FakeFile:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(Path, "open", lambda *a, **k: FakeFile())

    monkeypatch.setattr(
        "json.load",
        lambda *a, **k: (_ for _ in ()).throw(
            JSONDecodeError("Malformed JSON", doc="", pos=0)
        ),
    )

    result = client_erp.read_json_file(Path("malformed.json"))
    assert result is None
