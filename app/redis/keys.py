def job_key(job_id: str) -> str:
    return f"job:{job_id}"


def job_lock_key(job_id: str) -> str:
    return f"lock:job:{job_id}"
