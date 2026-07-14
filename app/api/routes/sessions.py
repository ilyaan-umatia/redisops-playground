from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import SessionServiceDependency
from app.models.session import Session, SessionCreate
from app.services.sessions import SessionNotFoundError

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreate, service: SessionServiceDependency) -> Session:
    return await service.create(request)


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: UUID, service: SessionServiceDependency) -> Session:
    try:
        return await service.get(str(session_id))
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        ) from exc


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: UUID, service: SessionServiceDependency) -> Response:
    try:
        await service.delete(str(session_id))
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
