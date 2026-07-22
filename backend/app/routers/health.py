from fastapi import APIRouter
from datetime import datetime, timezone
from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    is_ok = dynamodb_helper.health_check()
    db_status = "ok" if is_ok else "degraded"

    return HealthResponse(
        status="ok",
        db=db_status,
        timestamp=datetime.now(timezone.utc),
    )
