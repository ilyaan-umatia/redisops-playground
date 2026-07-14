from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import JobServiceDependency
from app.models.job import DeadLetterList, Job, JobCreate, JobList
from app.services.jobs import JobNotFoundError, JobNotRetryableError

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def create_job(request: JobCreate, service: JobServiceDependency) -> Job:
    return await service.create(request)


@router.get("", response_model=JobList)
async def list_jobs(
    service: JobServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobList:
    jobs = await service.list_recent(limit)
    return JobList(items=jobs, count=len(jobs))


@router.get("/dead-letter", response_model=DeadLetterList)
async def dead_letter_jobs(
    service: JobServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DeadLetterList:
    jobs = await service.dead_letters(limit)
    return DeadLetterList(items=jobs, count=len(jobs))


@router.post("/{job_id}/retry", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def retry_job(job_id: str, service: JobServiceDependency) -> Job:
    try:
        return await service.retry(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except JobNotRetryableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed jobs can be retried",
        ) from exc


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str, service: JobServiceDependency) -> Job:
    try:
        return await service.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
