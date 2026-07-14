import json
from datetime import UTC, datetime

from app.models.event import JobEventType
from app.models.job import JobStatus


def job_event_fields(
    event_type: JobEventType,
    job_id: str,
    status: JobStatus,
    *,
    timestamp: datetime | None = None,
    detail: dict[str, str | int | float | bool] | None = None,
) -> dict[str, str]:
    occurred_at = timestamp or datetime.now(UTC)
    return {
        "type": event_type.value,
        "job_id": job_id,
        "status": status.value,
        "timestamp": occurred_at.isoformat(),
        "detail": json.dumps(detail) if detail is not None else "",
    }
