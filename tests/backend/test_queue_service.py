from __future__ import annotations

from rq import Retry
from rq.job import Callback

from backend.app.services import queue_service


def test_enqueue_enrollment_job_sets_retry_and_failure_callback(monkeypatch):
    captured = {}

    class DummyQueue:
        def enqueue(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return object()

    monkeypatch.setattr(queue_service, "get_enrollment_queue", lambda: DummyQueue())

    queue_service.enqueue_enrollment_job({"job_id": "job_123"})

    assert captured["args"] == ("worker.app.jobs.process_enrollment_job", {"job_id": "job_123"})
    assert captured["kwargs"]["job_id"] == "job_123"

    retry = captured["kwargs"]["retry"]
    assert isinstance(retry, Retry)
    assert retry.max == 3
    assert retry.intervals == [5, 5, 5]

    callback = captured["kwargs"]["on_failure"]
    assert isinstance(callback, Callback)
    assert callback.func == "worker.app.jobs.mark_enrollment_job_failed_after_retries"
