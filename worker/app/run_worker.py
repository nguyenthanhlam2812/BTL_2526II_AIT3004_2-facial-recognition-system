from __future__ import annotations

import logging
import os

from redis import Redis
from rq import Connection, SimpleWorker, Worker
from rq.timeouts import TimerDeathPenalty

from backend.app.config import get_settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


class WindowsSimpleWorker(SimpleWorker):
    # RQ uses SIGALRM by default, which is not available on Windows.
    death_penalty_class = TimerDeathPenalty


def get_worker_class() -> type[Worker]:
    if os.name == "nt":
        return WindowsSimpleWorker
    return Worker


def main() -> None:
    settings = get_settings()
    redis_connection = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=get_int_env("REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS", 10),
        socket_keepalive=True,
        socket_timeout=get_int_env("REDIS_SOCKET_TIMEOUT_SECONDS", 600),
        health_check_interval=get_int_env("REDIS_HEALTH_CHECK_INTERVAL_SECONDS", 30),
    )
    with Connection(redis_connection):
        worker_class = get_worker_class()
        worker = worker_class(
            [settings.enrollment_queue],
            connection=redis_connection,
            default_worker_ttl=get_int_env("RQ_WORKER_TTL_SECONDS", 420),
        )
        worker.work()


if __name__ == "__main__":
    main()
