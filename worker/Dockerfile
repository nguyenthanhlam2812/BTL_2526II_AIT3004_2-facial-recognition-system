FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements ./requirements
RUN pip install --no-cache-dir -r requirements/worker.txt

COPY backend ./backend
COPY recognition ./recognition
COPY worker ./worker

CMD ["python", "-m", "worker.app.run_worker"]
