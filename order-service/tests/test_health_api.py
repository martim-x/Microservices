import pytest
from api.health.core import health_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def build_health_app(health_state: dict | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(health_router)

    app.state.services = {}
    if health_state is not None:
        app.state.services["health"] = health_state

    return app


def test_live() -> None:
    client = TestClient(build_health_app())

    response = client.get("/api/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_ready_success() -> None:
    client = TestClient(
        build_health_app(
            {
                "startup_complete": True,
                "shutdown_requested": False,
                "checks": {
                    "db": {"required": True, "ok": True},
                    "cache": {"required": True, "ok": True},
                    "order": {"required": True, "ok": True},
                    "mq": {"required": True, "ok": True},
                },
            }
        )
    )

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data


def test_ready_not_initialized() -> None:
    client = TestClient(build_health_app())

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "health state not initialized",
    }


@pytest.mark.parametrize(
    "health_state",
    [
        pytest.param(
            {
                "startup_complete": False,
                "shutdown_requested": False,
                "checks": {
                    "db": {"required": True, "ok": True},
                },
            },
            id="startup-incomplete",
        ),
        pytest.param(
            {
                "startup_complete": True,
                "shutdown_requested": True,
                "checks": {
                    "db": {"required": True, "ok": True},
                },
            },
            id="shutdown-requested",
        ),
        pytest.param(
            {
                "startup_complete": True,
                "shutdown_requested": False,
                "checks": {
                    "db": {"required": True, "ok": False},
                },
            },
            id="required-check-failed",
        ),
    ],
)
def test_ready_not_ready(health_state: dict) -> None:
    client = TestClient(build_health_app(health_state))

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["reason"] == "startup incomplete or dependency failed"
    assert "checks" in data


def test_full_success() -> None:
    client = TestClient(
        build_health_app(
            {
                "startup_complete": True,
                "shutdown_requested": False,
                "checks": {
                    "db": {"required": True, "ok": True},
                    "cache": {"required": True, "ok": True},
                    "mq": {"required": True, "ok": True},
                },
            }
        )
    )

    response = client.get("/api/health/full")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["startup_complete"] is True
    assert data["shutdown_requested"] is False
    assert "checks" in data
    assert "timestamp" in data


def test_full_unhealthy_not_initialized() -> None:
    client = TestClient(build_health_app())

    response = client.get("/api/health/full")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "reason": "health state not initialized",
    }
