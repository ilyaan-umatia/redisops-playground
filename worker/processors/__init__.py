from collections.abc import Callable

from app.models.job import JobType
from worker.processors.report import generate_report

JobPayload = dict[str, str | int | float | bool]
JobResult = dict[str, str | int | float | bool]
Processor = Callable[[JobPayload], JobResult]

PROCESSORS: dict[JobType, Processor] = {
    JobType.REPORT_GENERATION: generate_report,
}
