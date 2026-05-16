FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements ./requirements
RUN pip install --no-cache-dir -r requirements/backend.txt

COPY alembic.ini ./alembic.ini
COPY backend ./backend
COPY recognition ./recognition
COPY scripts ./scripts

EXPOSE 8000

CMD ["python", "-m", "backend.docker_entrypoint"]
