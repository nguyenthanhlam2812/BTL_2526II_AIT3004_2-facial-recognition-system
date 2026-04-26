from __future__ import annotations

import logging

from redis import Redis
from rq import Connection, Worker

from backend.app.config import get_settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    settings = get_settings()
    redis_connection = Redis.from_url(settings.redis_url)
    with Connection(redis_connection):
        worker = Worker([settings.enrollment_queue])
        worker.work()


if __name__ == "__main__":
    main()
