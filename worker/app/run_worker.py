from __future__ import annotations

import logging
import os

from redis import Redis
from rq import Connection, SimpleWorker, Worker
from rq.timeouts import TimerDeathPenalty

from backend.app.config import get_settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


class WindowsSimpleWorker(SimpleWorker):
    # RQ uses SIGALRM by default, which is not available on Windows.
    death_penalty_class = TimerDeathPenalty


def get_worker_class() -> type[Worker]:
    if os.name == "nt":
        return WindowsSimpleWorker
    return Worker


def main() -> None:
    settings = get_settings()
    redis_connection = Redis.from_url(settings.redis_url)
    with Connection(redis_connection):
        worker_class = get_worker_class()
        worker = worker_class([settings.enrollment_queue])
        worker.work()


if __name__ == "__main__":
    main()
