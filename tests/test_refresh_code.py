"""Tests for refresh_code, the HTTP-deployment self-update tool.

Offline: MONARCH_SOURCE is pointed at a dummy URL and the archive download
helper is monkeypatched, so no network or process exit happens.
"""

from pathlib import Path

import pytest

import server


def _current_source() -> bytes:
    return Path(server.__file__).read_bytes()


@pytest.fixture
def _source_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MONARCH_SOURCE", "https://example.test/monarch-mcp.zip")
    monkeypatch.setenv("MONARCH_REF", "refs/heads/add-refresh-code")


class TestRefreshCode:
    @pytest.mark.asyncio
    async def test_error_when_source_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MONARCH_SOURCE", raising=False)
        result = await server.refresh_code()
        assert result.status == "error"
        assert "MONARCH_SOURCE" in (result.detail or "")

    @pytest.mark.asyncio
    async def test_already_current(self, monkeypatch: pytest.MonkeyPatch, _source_env: None) -> None:
        monkeypatch.setattr(server, "_fetch_deployed_server_source", lambda url: _current_source())
        restart = []
        monkeypatch.setattr(server, "_schedule_restart", lambda: restart.append(True))
        result = await server.refresh_code()
        assert result.status == "already_current"
        assert result.ref == "refs/heads/add-refresh-code"
        assert restart == []

    @pytest.mark.asyncio
    async def test_updated_schedules_restart(self, monkeypatch: pytest.MonkeyPatch, _source_env: None) -> None:
        monkeypatch.setattr(server, "_fetch_deployed_server_source", lambda url: b"# changed\n" + _current_source())
        restart = []
        monkeypatch.setattr(server, "_schedule_restart", lambda: restart.append(True))
        result = await server.refresh_code()
        assert result.status == "updated"
        assert restart == [True]

    @pytest.mark.asyncio
    async def test_uncompilable_download_is_error(self, monkeypatch: pytest.MonkeyPatch, _source_env: None) -> None:
        monkeypatch.setattr(server, "_fetch_deployed_server_source", lambda url: b"def broken(:\n")
        result = await server.refresh_code()
        assert result.status == "error"
        assert "does not compile" in (result.detail or "")

    @pytest.mark.asyncio
    async def test_download_failure_is_error(self, monkeypatch: pytest.MonkeyPatch, _source_env: None) -> None:
        def _boom(url: str) -> bytes:
            raise OSError("no network")

        monkeypatch.setattr(server, "_fetch_deployed_server_source", _boom)
        result = await server.refresh_code()
        assert result.status == "error"
        assert "could not download" in (result.detail or "")
