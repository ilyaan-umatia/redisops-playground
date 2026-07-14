from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import JobServiceDependency
from app.models.job import Job, JobCreate
from app.services.jobs import JobNotFoundError

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def create_job(request: JobCreate, service: JobServiceDependency) -> Job:
    return await service.create(request)


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str, service: JobServiceDependency) -> Job:
    try:
        return await service.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
