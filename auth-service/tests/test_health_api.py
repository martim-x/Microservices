import pytest
from api.health.core import health_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def build_health_app(health_state=None) -> FastAPI:
    app = FastAPI()
    app.include_router(health_router)

    if health_state is not None:
        app.state.services = {"health": health_state}

    return app


def test_live() -> None:
    client = TestClient(build_health_app())

    response = client.get("/api/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_ready_success() -> None:
    app = build_health_app(
        {
            "startup_complete": True,
            "shutdown_requested": False,
            "checks": {
                "db": {"required": True, "ok": True},
                "redis": {"required": True, "ok": True},
                "metrics": {"required": False, "ok": False},
            },
        }
    )
    client = TestClient(app)

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["db"]["ok"] is True


def test_ready_no_health_state() -> None:
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
                    "redis": {"required": True, "ok": True},
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


def test_full_unhealthy_when_state_missing() -> None:
    client = TestClient(build_health_app())

    response = client.get("/api/health/full")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "reason": "health state not initialized",
    }


def test_full_unhealthy_when_required_check_failed() -> None:
    client = TestClient(
        build_health_app(
            {
                "startup_complete": True,
                "shutdown_requested": False,
                "checks": {
                    "db": {"required": True, "ok": False},
                    "redis": {"required": False, "ok": False},
                },
            }
        )
    )

    response = client.get("/api/health/full")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["startup_complete"] is True
    assert data["shutdown_requested"] is False
    assert data["checks"]["db"]["ok"] is False
    assert "timestamp" in data
