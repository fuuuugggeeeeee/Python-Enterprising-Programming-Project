"""Read-only audit-event endpoint."""

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_service, require_admin
from ..models import UserRecord
from ..schemas import AuditListResponse, AuditResponse
from ..services import ApiService

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=AuditListResponse)
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ApiService = Depends(get_service),
    _: UserRecord = Depends(require_admin),
) -> AuditListResponse:
    events, total = service.list_audit_events(limit, offset)
    return AuditListResponse(
        items=[AuditResponse.model_validate(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
    )
