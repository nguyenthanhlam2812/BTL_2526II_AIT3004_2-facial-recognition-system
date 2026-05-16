from __future__ import annotations

from typing import Any

from redis import Redis
from rq import Queue, Retry
from rq.job import Callback

from backend.app.config import get_settings


class QueueUnavailableError(Exception):
    pass


def get_enrollment_queue() -> Queue:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    return Queue(
        settings.enrollment_queue,
        connection=connection,
        default_timeout=600,
    )


def enqueue_enrollment_job(payload: dict[str, Any]) -> None:
    try:
        queue = get_enrollment_queue()
        queue.enqueue(
            "worker.app.jobs.process_enrollment_job",
            payload,
            job_id=payload["job_id"],
            retry=Retry(max=3, interval=[5, 5, 5]),
            on_failure=Callback("worker.app.jobs.mark_enrollment_job_failed_after_retries"),
        )
    except Exception as exc:
        raise QueueUnavailableError("Cannot enqueue enrollment job.") from exc
