import pytest
from api.health.core import health_router
from api.health.health import _is_ready
from fastapi import FastAPI
from fastapi.testclient import TestClient


def build_health_app(health_state=None) -> FastAPI:
    app = FastAPI()
    app.include_router(health_router)

    if health_state is not None:
        app.state.services = {"health": health_state}

    return app


def test_is_ready_success() -> None:
    health = {
        "startup_complete": True,
        "shutdown_requested": False,
        "checks": {"db": {"required": True, "ok": True}},
    }

    assert _is_ready(health) is True


@pytest.mark.parametrize(
    "health",
    [
        {
            "startup_complete": False,
            "shutdown_requested": False,
            "checks": {"db": {"required": True, "ok": True}},
        },
        {
            "startup_complete": True,
            "shutdown_requested": True,
            "checks": {"db": {"required": True, "ok": True}},
        },
        {
            "startup_complete": True,
            "shutdown_requested": False,
            "checks": {"db": {"required": True, "ok": False}},
        },
    ],
)
def test_is_ready_false(health: dict) -> None:
    assert _is_ready(health) is False


def test_live() -> None:
    client = TestClient(build_health_app())

    response = client.get("/api/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_ready_no_health_state() -> None:
    client = TestClient(build_health_app())

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "health state not initialized",
    }


def test_ready_success() -> None:
    client = TestClient(
        build_health_app(
            {
                "startup_complete": True,
                "shutdown_requested": False,
                "checks": {"db": {"required": True, "ok": True}},
            }
        )
    )

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_not_ready() -> None:
    client = TestClient(
        build_health_app(
            {
                "startup_complete": True,
                "shutdown_requested": False,
                "checks": {"db": {"required": True, "ok": False}},
            }
        )
    )

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_full_no_health_state() -> None:
    client = TestClient(build_health_app())

    response = client.get("/api/health/full")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "reason": "health state not initialized",
    }


def test_full_healthy() -> None:
    client = TestClient(
        build_health_app(
            {
                "startup_complete": True,
                "shutdown_requested": False,
                "checks": {"db": {"required": True, "ok": True}},
            }
        )
    )

    response = client.get("/api/health/full")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_full_unhealthy() -> None:
    client = TestClient(
        build_health_app(
            {
                "startup_complete": True,
                "shutdown_requested": False,
                "checks": {"db": {"required": True, "ok": False}},
            }
        )
    )

    response = client.get("/api/health/full")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
