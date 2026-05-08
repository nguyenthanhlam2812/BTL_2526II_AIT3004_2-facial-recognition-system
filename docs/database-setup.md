# Thiết lập database và dependency

Cập nhật: `2026-05-08`.

Project có 2 chế độ:

- Local dev: backend/worker chạy bằng `.venv`, dùng `.env`.
- Docker: backend/worker/dependencies chạy bằng Compose, dùng `.env.docker.example` và có thể override bằng `.env.docker`.

## Env files

| File | Mục đích |
| --- | --- |
| `.env` | Local dev |
| `.env.example` | Mẫu local dev |
| `.env.docker` | Override Docker, không bắt buộc |
| `.env.docker.example` | Mặc định cho Docker Compose |

Port cần nhớ:

- MySQL local của bạn có thể dùng `3307`.
- MySQL Docker đang map host port `3306`.
- Không cần đổi MySQL local về `3306` vì `.env` và `.env.docker.example` tách nhau.

## Local MySQL

Tạo database:

```sql
CREATE DATABASE IF NOT EXISTS face_attendance
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Tạo user:

```sql
CREATE USER IF NOT EXISTS 'app'@'localhost' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'app'@'localhost';

CREATE USER IF NOT EXISTS 'app'@'127.0.0.1' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'app'@'127.0.0.1';

FLUSH PRIVILEGES;
```

Nếu MySQL local chạy port `3307`, `.env` nên có:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_DATABASE=face_attendance
MYSQL_USER=app
MYSQL_PASSWORD=app_password
```

Chạy migration và seed:

```powershell
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python scripts\seed\seed_admin.py
```

Kiểm tra kết nối:

```powershell
.\.venv\Scripts\python -c "from sqlalchemy import text; from backend.app.db.session import engine; conn = engine.connect(); print(conn.execute(text('SELECT 1')).scalar()); conn.close()"
```

In ra `1` là ổn.

## Docker backend stack

```powershell
docker compose build backend worker
docker compose up -d mysql redis minio qdrant backend worker
docker compose ps
```

Backend container tự:

1. Wait MySQL.
2. Chạy `alembic upgrade head` nếu `RUN_MIGRATIONS=true`.
3. Chạy `scripts/seed/seed_admin.py` nếu `SEED_ADMIN=true`.
4. Start Uvicorn.

Kiểm tra logs:

```powershell
docker compose logs backend --tail=150
docker compose logs worker --tail=120
```

## Nguyên tắc

- Không tạo bảng tay rồi bỏ qua migration.
- Không hard-code host/port DB trong code.
- Không dùng root cho app logic.
- Khi thêm env key mới, cập nhật cả `.env.example` và `.env.docker.example`.
