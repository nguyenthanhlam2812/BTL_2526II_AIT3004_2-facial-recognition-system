from __future__ import annotations

import os
import subprocess
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.config import get_settings


def _env_enabled(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def wait_for_database() -> None:
    settings = get_settings()
    max_attempts = int(os.getenv("DB_WAIT_MAX_ATTEMPTS", "30"))
    wait_seconds = float(os.getenv("DB_WAIT_SECONDS", "2"))
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        engine = create_engine(settings.mysql_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("Database is ready.", flush=True)
            return
        except SQLAlchemyError as exc:
            last_error = exc
            print(
                f"Waiting for database ({attempt}/{max_attempts})...",
                flush=True,
            )
            time.sleep(wait_seconds)
        finally:
            engine.dispose()

    raise RuntimeError("Database did not become ready in time.") from last_error


def run_command(command: list[str]) -> None:
    print(f"Running: {' '.join(command)}", flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    wait_for_database()

    if _env_enabled("RUN_MIGRATIONS"):
        run_command([sys.executable, "-m", "alembic", "upgrade", "head"])

    if _env_enabled("SEED_ADMIN"):
        run_command([sys.executable, "scripts/seed/seed_admin.py"])

    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
    )


if __name__ == "__main__":
    main()
