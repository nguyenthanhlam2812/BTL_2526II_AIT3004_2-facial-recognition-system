# Hợp đồng API

Cập nhật: `2026-05-09`.

Contract này dùng cho frontend admin/kiosk bám theo backend hiện tại.

## Quy ước

- Prefix: `/api`
- Auth admin: Bearer token.
- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Tài khoản seed: `admin` / `admin123`
- Lỗi FastAPI hiện có thể trả field `detail`.

## Auth

### `POST /api/auth/login`

Request:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

Response:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

## Employee

Fields chính:

- `employee_code`: required, unique.
- `full_name`: required.
- `department`: required.
- `position`: required.
- `status`: `active` hoặc `inactive`.

### `GET /api/employees`

Query: `q`, `page`, `page_size`.

Response:

```json
{
  "items": [
    {
      "id": 1,
      "employee_code": "E001",
      "full_name": "Nguyen Van A",
      "department": "IT",
      "position": "Engineer",
      "status": "active",
      "created_at": "2026-05-08T10:00:00Z",
      "updated_at": "2026-05-08T10:00:00Z"
    }
  ],
  "total": 1
}
```

### `POST /api/employees`

```json
{
  "employee_code": "E001",
  "full_name": "Nguyen Van A",
  "department": "IT",
  "position": "Engineer",
  "status": "active"
}
```

### `PUT /api/employees/{employee_id}`

Body giống `POST /api/employees`.

### `DELETE /api/employees/{employee_id}`

```json
{
  "ok": true
}
```

## Enrollment

### `POST /api/employees/{employee_id}/enrollments`

Cần auth admin.

Content type: `multipart/form-data`

Fields:

- `files`: 1-5 ảnh.

Response:

```json
{
  "employee_id": 1,
  "job_id": "job_123",
  "status": "pending",
  "uploaded_count": 3
}
```

### `GET /api/enrollments/{job_id}`

Cần auth admin.

```json
{
  "job_id": "job_123",
  "employee_id": 1,
  "status": "success",
  "message": "Embedding created",
  "processed_count": 3,
  "failed_count": 0
}
```

## Attendance

### `POST /api/attendance/frame`

Hiện chưa bắt auth để kiosk gọi trực tiếp trong MVP.

Content type: `multipart/form-data`

Fields:

- `image`: required, JPEG/PNG.
- `action_type`: `check_in` hoặc `check_out`.
- `captured_at`: optional ISO datetime.
- `camera_id`: optional string.

Response khi match:

```json
{
  "matched": true,
  "employee": {
    "id": 1,
    "employee_code": "E001",
    "full_name": "Nguyen Van A"
  },
  "score": 0.86,
  "action_type": "check_in",
  "attendance_status": "recorded",
  "message": "Check-in recorded.",
  "event_id": 101
}
```

Response khi unknown/multiple:

```json
{
  "matched": false,
  "employee": null,
  "score": null,
  "action_type": "check_in",
  "attendance_status": "unknown_face",
  "message": "Face not recognized.",
  "event_id": 102
}
```

`attendance_status` có thể là:

- `recorded`
- `unknown_face`
- `multiple_faces`

### `GET /api/attendance/events`

Cần auth admin.

Query: `employee_id`, `action_type`, `from`, `to`, `page`, `page_size`.

Response:

```json
{
  "items": [
    {
      "id": 101,
      "created_at": "2026-05-08T10:30:00Z",
      "captured_at": "2026-05-08T10:30:00Z",
      "action_type": "check_in",
      "attendance_status": "recorded",
      "score": 0.86,
      "camera_id": "cam-01",
      "snapshot_object_key": null,
      "employee": {
        "id": 1,
        "employee_code": "E001",
        "full_name": "Nguyen Van A"
      }
    }
  ],
  "total": 1
}
```

## System

### `GET /api/system/settings`

Cần auth admin.

Endpoint này chỉ trả cấu hình không nhạy cảm để Admin UI hiển thị read-only. Response không chứa secret như `JWT_SECRET_KEY`, `MYSQL_PASSWORD`, `MINIO_SECRET_KEY`.

Response:

```json
{
  "environment": "development",
  "api_prefix": "/api",
  "attendance_threshold": 0.3,
  "insightface_model_name": "buffalo_l",
  "face_min_det_score": 0.5,
  "face_min_area_ratio": 0.015,
  "face_secondary_area_ratio": 0.35,
  "warmup_face_model": true,
  "qdrant_url": "http://qdrant:6333",
  "qdrant_collection_employee_faces": "employee_faces",
  "minio_endpoint": "minio:9000",
  "redis": {
    "scheme": "redis",
    "host": "redis",
    "port": 6379,
    "database": 0
  }
}
```

## Healthcheck

### `GET /healthz`

```json
{
  "status": "ok"
}
```
