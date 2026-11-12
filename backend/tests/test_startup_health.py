from types import SimpleNamespace
import alembic.command
import alembic.config
import pytest

from app.main import app, health_ready, lifespan


class _AsyncCtx:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.anyio
async def test_lifespan_fails_fast_on_alembic_error_by_default(monkeypatch):
    monkeypatch.setenv("RUN_ALEMBIC_MIGRATIONS", "1")
    monkeypatch.setenv("RUN_BOOTSTRAP_MIGRATIONS", "0")
    monkeypatch.delenv("ALLOW_MIGRATION_FAILURE", raising=False)

    monkeypatch.setattr(alembic.config, "Config", lambda *a, **kw: object())

    def _boom(*args, **kwargs):
        raise RuntimeError("alembic revision head conflict")

    monkeypatch.setattr(alembic.command, "upgrade", _boom)

    try:
        with pytest.raises(RuntimeError, match="Alembic migration failed"):
            async with lifespan(app):
                pass
        assert app.state.migration_status == "failed"
    finally:
        app.state.migration_status = "ok"
        app.state.migration_error = None


@pytest.mark.anyio
async def test_lifespan_degrades_readiness_when_migration_failure_allowed(monkeypatch):
    monkeypatch.setenv("RUN_ALEMBIC_MIGRATIONS", "1")
    monkeypatch.setenv("RUN_BOOTSTRAP_MIGRATIONS", "0")
    monkeypatch.setenv("ALLOW_MIGRATION_FAILURE", "1")

    monkeypatch.setattr(alembic.config, "Config", lambda *a, **kw: object())

    def _boom(*args, **kwargs):
        raise RuntimeError("temporary migration lock")

    monkeypatch.setattr(alembic.command, "upgrade", _boom)

    class _HealthyDB:
        async def execute(self, _stmt):
            return 1

    monkeypatch.setattr("app.main.AsyncSessionLocal", lambda: _AsyncCtx(_HealthyDB()))
    monkeypatch.setattr(
        "app.services.vectorstore.chroma_store._get_cached_persistent_client",
        lambda _dir: SimpleNamespace(heartbeat=lambda: 1),
    )

    try:
        async with lifespan(app):
            resp = await health_ready()
            assert resp.status_code == 503
            import json
            body = json.loads(resp.body.decode())
            assert body["status"] == "degraded"
            assert "temporary migration lock" in body["checks"]["migrations"]
    finally:
        app.state.migration_status = "ok"
        app.state.migration_error = None
