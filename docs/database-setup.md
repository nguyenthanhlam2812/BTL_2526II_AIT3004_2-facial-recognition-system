# Thiết lập database và env

Dự án có 2 chế độ:

- Phát triển local: backend/worker chạy bằng `.venv`, dùng `.env`
- Docker: backend/worker/các dịch vụ phụ trợ chạy bằng Compose, dùng `.env.docker.example` và có thể ghi đè bằng `.env.docker`

## File env

| File | Mục đích |
| --- | --- |
| `.env` | Phát triển local |
| `.env.example` | Mẫu local dev |
| `.env.docker` | Ghi đè cấu hình Docker, không bắt buộc |
| `.env.docker.example` | Mặc định cho Docker Compose |

## Env cho admin/public demo

| Key | Mặc định | Mục đích |
| --- | --- | --- |
| `SEED_ADMIN` | `true` | Cho phép backend entrypoint tạo seed admin nếu user chưa tồn tại |
| `SEED_ADMIN_USERNAME` | `admin` | Tên đăng nhập admin được seed |
| `SEED_ADMIN_PASSWORD` | `admin123` | Mật khẩu admin local/demo mặc định |
| `JWT_SECRET_KEY` | `change-me` | Secret ký JWT |
| `KIOSK_API_TOKEN` | `local-kiosk-token` | Token dùng chung cho `POST /api/attendance/frame` |
| `PUBLIC_DEMO_MODE` | `false` | Bật fail-safe startup cho public demo path |
| `BUSINESS_TIMEZONE` | `Asia/Ho_Chi_Minh` | Múi giờ nghiệp vụ cho history/report/dashboard |

Nếu bật Cloudflare Tunnel hoặc mở hệ thống ra Internet:

1. Tạo `.env.docker`
2. Đổi `SEED_ADMIN_PASSWORD`
3. Đổi `JWT_SECRET_KEY`
4. Đổi `KIOSK_API_TOKEN`
5. Chạy Compose kèm `docker-compose.tunnel.yml`

Seed admin chỉ dùng để bootstrap tài khoản ban đầu. Nếu user đã tồn tại, script seed sẽ không ghi đè password, role hay trạng thái đã được đổi trong UI.

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

## Docker backend stack

```powershell
docker compose build backend worker
docker compose up -d mysql redis minio qdrant backend worker
docker compose ps
```

Luồng public demo:

```powershell
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel up -d
```

Backend container tự:

1. Chờ MySQL
2. Chạy `alembic upgrade head` nếu `RUN_MIGRATIONS=true`
3. Chạy `scripts/seed/seed_admin.py` nếu `SEED_ADMIN=true`
4. Kiểm tra runtime settings nếu `PUBLIC_DEMO_MODE=true`
5. Khởi động Uvicorn

## Nguyên tắc

- Không tạo bảng tay rồi bỏ qua migration
- Không gắn cứng host/port DB trong code
- Không dùng root cho app logic
- Khi thêm env key mới, cập nhật cả `.env.example` và `.env.docker.example`
