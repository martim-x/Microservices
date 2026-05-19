from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status

local_router = APIRouter(prefix="")


def _is_ready(health: dict) -> bool:
    if not health["startup_complete"]:
        return False
    if health["shutdown_requested"]:
        return False

    for check in health["checks"].values():
        if check.get("required") and not check.get("ok"):
            return False

    return True


@local_router.get(
    "/live",
    status_code=status.HTTP_200_OK,
)
async def live(request: Request):
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC),
    }


@local_router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
)
async def ready(request: Request, response: Response):
    try:
        health = request.app.state.services["health"]
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": "health state not initialized",
        }

    if not _is_ready(health):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": "startup incomplete or dependency failed",
            "checks": health["checks"],
        }

    response.status_code = status.HTTP_200_OK
    return {
        "status": "ready",
        "checks": health["checks"],
    }


@local_router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def health_full(request: Request, response: Response):
    try:
        health = request.app.state.services["health"]
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "reason": "health state not initialized",
        }

    overall_ready = _is_ready(health)

    response.status_code = (
        status.HTTP_200_OK if overall_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return {
        "status": "healthy" if overall_ready else "unhealthy",
        "startup_complete": health["startup_complete"],
        "shutdown_requested": health["shutdown_requested"],
        "checks": health["checks"],
        "timestamp": datetime.now(UTC),
    }
