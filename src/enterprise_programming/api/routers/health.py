"""Liveness, readiness, and metrics endpoints."""

from fastapi import APIRouter, Request, Response, status

from enterprise_programming import __version__

from ..observability import metrics_response
from ..schemas import LivenessResponse, ReadinessResponse

router = APIRouter(tags=["operations"])


@router.get("/health/live", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok", version=__version__)


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness(request: Request, response: Response) -> ReadinessResponse:
    ready = request.app.state.database.is_ready()
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ok" if ready else "unavailable",
        version=__version__,
        database="up" if ready else "down",
    )


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return metrics_response()
