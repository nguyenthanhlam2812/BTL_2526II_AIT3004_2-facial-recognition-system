# Thiết lập Database Cho Giai Đoạn Local

Tài liệu này chốt cách làm hiện tại: dùng **MySQL Server local trên máy** để phát triển schema và migration trước, sau đó mới chuyển sang **Docker Compose** khi cần đóng gói và bàn giao.

## 1. Dùng tool nào

- **MySQL Workbench**: tạo database, user, kiểm tra bảng bằng giao diện.
- **PowerShell**: chạy lệnh trong project.
- **VS Code**: viết model, migration, backend code.
- **SQLAlchemy**: định nghĩa schema bằng model Python.
- **Alembic**: sinh và chạy migration.

## 2. File nào đang dùng cho local và Docker

- `.env`: cấu hình **local hiện tại**
- `.env.example`: mẫu cấu hình local để copy cho máy khác
- `.env.docker`: cấu hình cho **backend/worker khi chạy trong Docker**
- `.env.docker.example`: mẫu cấu hình Docker để bàn giao

Quy ước hiện tại:

- Khi chạy backend local: dùng `.env`
- Khi chạy backend/worker trong Docker: `docker-compose.yml` sẽ đọc `.env.docker`

Nhờ vậy code không phải sửa khi đổi môi trường. Chỉ đổi file env.

## 3. Bắt đầu từ đâu

### Bước 1: Đảm bảo MySQL local đang chạy

Máy hiện có `MySQL80` local. Có thể kiểm tra nhanh bằng PowerShell:

```powershell
Get-Service MySQL80
```

Hoặc dùng luôn command line:

```powershell
mysql --version
```

### Bước 2: Tạo database `face_attendance`

Trong **MySQL Workbench**:

1. Mở kết nối vào `MySQL80`
2. Mở tab query mới
3. Chạy:

```sql
CREATE DATABASE IF NOT EXISTS face_attendance
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

### Bước 3: Tạo user ứng dụng

Nếu muốn bám đúng `.env`, tạo luôn user `app`:

```sql
CREATE USER IF NOT EXISTS 'app'@'localhost' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'app'@'localhost';
FLUSH PRIVILEGES;
```

Nếu backend chạy local mà không dùng `localhost`, có thể thêm:

```sql
CREATE USER IF NOT EXISTS 'app'@'127.0.0.1' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

### Bước 4: Kiểm tra `.env`

File `.env` hiện đã được chỉnh cho local:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=face_attendance
MYSQL_USER=app
MYSQL_PASSWORD=app_password
```

## 4. Chuẩn bị code cho bước tạo schema

Phần chuẩn bị đã có sẵn trong repo:

- `backend/app/config.py`: tạo `mysql_url` từ `.env`
- `backend/app/db/base.py`: khai báo `Base` cho SQLAlchemy
- `backend/app/db/session.py`: tạo `engine`, `SessionLocal`, `get_db`
- `backend/app/models/__init__.py`: chỗ tập hợp model cho Alembic

Việc tiếp theo bạn sẽ làm ở các file mới trong `backend/app/models/`:

- `user.py`
- `employee.py`
- `enrollment.py`
- `enrollment_image.py`
- `attendance_event.py`

## 5. Cài package cần cho database và migration

Trong thư mục gốc project:

```powershell
.venv\Scripts\pip install -r requirements\backend.txt
```

`requirements/backend.txt` hiện đã có thêm `alembic`, nên đây là lệnh cài cần dùng cho bước tiếp theo.

## 6. Trình tự làm tiếp theo

Sau khi database local đã tạo xong, làm theo đúng thứ tự sau:

1. Tạo các file model trong `backend/app/models/`
2. Import tất cả model vào `backend/app/models/__init__.py`
3. Khởi tạo Alembic trong `backend/`
4. Cấu hình Alembic dùng `backend.app.config.get_settings().mysql_url`
5. Sinh migration đầu tiên
6. Chạy migration vào `face_attendance`
7. Kiểm tra lại bảng trong Workbench

## 7. Lệnh sẽ dùng ở bước tiếp theo

Sau khi có model, các lệnh chính sẽ là:

```powershell
.venv\Scripts\alembic init backend\alembic
.venv\Scripts\alembic -c backend\alembic.ini revision --autogenerate -m "initial schema"
.venv\Scripts\alembic -c backend\alembic.ini upgrade head
```

## 8. Sau này chuyển sang Docker thì làm gì

Khi cần chạy full stack bằng Docker:

1. Copy:

```powershell
Copy-Item .env.docker.example .env.docker
```

2. Chạy:

```powershell
docker compose --env-file .env.docker up -d mysql redis minio qdrant backend worker
```

3. Vì `docker-compose.yml` đã cấu hình `backend` và `worker` đọc `.env.docker`, còn `--env-file .env.docker` giúp toàn bộ stack lấy đúng biến Docker, code không cần sửa lại.

## 9. Điều không nên làm

- Không tạo bảng bằng tay trong Workbench rồi bỏ qua migration
- Không hard-code host DB trong code
- Không dùng root account cho toàn bộ app logic
- Không để local schema và Docker schema lệch nhau
