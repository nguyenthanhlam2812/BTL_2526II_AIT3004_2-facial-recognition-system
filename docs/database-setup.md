# Thiet lap database va env

Cap nhat: `2026-05-11`.

Project co 2 che do:

- Local dev: backend/worker chay bang `.venv`, dung `.env`
- Docker: backend/worker/dependencies chay bang Compose, dung `.env.docker.example` va co the override bang `.env.docker`

## Env files

| File | Muc dich |
| --- | --- |
| `.env` | Local dev |
| `.env.example` | Mau local dev |
| `.env.docker` | Override Docker, khong bat buoc |
| `.env.docker.example` | Mac dinh cho Docker Compose |

## Admin/public demo env

| Key | Mac dinh | Muc dich |
| --- | --- | --- |
| `SEED_ADMIN` | `true` | Cho phep backend entrypoint tao seed admin neu user chua ton tai |
| `SEED_ADMIN_USERNAME` | `admin` | Username admin duoc seed |
| `SEED_ADMIN_PASSWORD` | `admin123` | Password admin local/demo mac dinh |
| `JWT_SECRET_KEY` | `change-me` | Secret ky JWT |
| `KIOSK_API_TOKEN` | `local-kiosk-token` | Shared token cho `POST /api/attendance/frame` |
| `PUBLIC_DEMO_MODE` | `false` | Bat fail-safe startup cho public demo path |
| `BUSINESS_TIMEZONE` | `Asia/Ho_Chi_Minh` | Timezone nghiep vu cho history/report/dashboard |

Neu bat Cloudflare Tunnel hoac expose he thong ra Internet:

1. Tao `.env.docker`
2. Doi `SEED_ADMIN_PASSWORD`
3. Doi `JWT_SECRET_KEY`
4. Doi `KIOSK_API_TOKEN`
5. Chay Compose kem `docker-compose.tunnel.yml`

Seed admin chi dung de bootstrap tai khoan ban dau. Neu user da ton tai, script seed se khong ghi de password, role hay trang thai da duoc doi trong UI.

## Local MySQL

Tao database:

```sql
CREATE DATABASE IF NOT EXISTS face_attendance
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Tao user:

```sql
CREATE USER IF NOT EXISTS 'app'@'localhost' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'app'@'localhost';

CREATE USER IF NOT EXISTS 'app'@'127.0.0.1' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'app'@'127.0.0.1';

FLUSH PRIVILEGES;
```

Neu MySQL local chay port `3307`, `.env` nen co:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_DATABASE=face_attendance
MYSQL_USER=app
MYSQL_PASSWORD=app_password
```

Chay migration va seed:

```powershell
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python scripts\seed\seed_admin.py
```

## Docker backend stack

```powershell
docker compose build backend worker
docker compose up -d mysql redis minio qdrant backend worker
docker compose ps
```

Public demo path:

```powershell
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel up -d
```

Backend container tu:

1. Wait MySQL
2. Chay `alembic upgrade head` neu `RUN_MIGRATIONS=true`
3. Chay `scripts/seed/seed_admin.py` neu `SEED_ADMIN=true`
4. Validate runtime settings neu `PUBLIC_DEMO_MODE=true`
5. Start Uvicorn

## Nguyen tac

- Khong tao bang tay roi bo qua migration
- Khong hard-code host/port DB trong code
- Khong dung root cho app logic
- Khi them env key moi, cap nhat ca `.env.example` va `.env.docker.example`
