# Hợp đồng API

Tài liệu này dùng cho frontend admin/kiosk bám theo backend hiện tại.

## Quy ước

- Prefix: `/api`
- Auth admin: Bearer token.
- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Tài khoản seed: `admin` / `admin123`
- FastAPI có thể trả lỗi qua field `detail`.

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
    "role": "owner"
  }
}
```

### `POST /api/auth/change-password`

Yêu cầu đăng nhập.

```json
{
  "current_password": "admin123",
  "new_password": "new-password-123"
}
```

Response:

```json
{
  "ok": true,
  "message": "Password updated successfully."
}
```

## Nhân viên

Trường chính:

- `employee_code`: required, unique.
- `full_name`: required.
- `department`: required.
- `position`: required.
- `status`: `active` hoặc `inactive`.

### `GET /api/employees`

Yêu cầu đăng nhập vào admin console.

Query: `q`, `department`, `page`, `page_size`.

Response:

```json
{
  "items": [
    {
      "id": 1,
      "employee_code": "E001",
      "full_name": "Nguyễn Văn A",
      "department": "IT",
      "position": "Engineer",
      "status": "active",
      "face_data_status": "enrolled",
      "created_at": "2026-05-08T10:00:00Z",
      "updated_at": "2026-05-08T10:00:00Z"
    }
  ],
  "total": 1
}
```

### `POST /api/employees`

Yêu cầu quyền operator (`owner` hoặc `admin`).

```json
{
  "employee_code": "E001",
  "full_name": "Nguyễn Văn A",
  "department": "IT",
  "position": "Engineer",
  "status": "active"
}
```

### `PUT /api/employees/{employee_id}`

Yêu cầu quyền operator (`owner` hoặc `admin`).

Body giống `POST /api/employees`.

### `DELETE /api/employees/{employee_id}`

Yêu cầu quyền operator (`owner` hoặc `admin`).

```json
{
  "ok": true
}
```

### `GET /api/employees/departments`

Yêu cầu đăng nhập vào admin console.

Response:

```json
["IT", "HR", "Operations"]
```

## Enrollment

### `POST /api/employees/{employee_id}/enrollments`

Yêu cầu quyền operator (`owner` hoặc `admin`).

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

Yêu cầu đăng nhập vào admin console.

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

Kiosk route là public ở frontend, nhưng backend yêu cầu header `X-Kiosk-Token` khi gọi trực tiếp.

Content type: `multipart/form-data`

Fields:

- `image`: required, JPEG/PNG.
- `action_type`: `check_in` hoặc `check_out`.
- `captured_at`: optional ISO datetime.
- `camera_id`: optional string.
- `record_unmatched`: optional boolean.

Lưu ý:

- Gọi thẳng vào backend không có `X-Kiosk-Token` sẽ trả `401`.
- Endpoint có rate limit `10 requests/second` và có thể trả `429`.

Response khi match:

```json
{
  "matched": true,
  "employee": {
    "id": 1,
    "employee_code": "E001",
    "full_name": "Nguyễn Văn A"
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

### `GET /api/attendance/reports/daily`

Yêu cầu đăng nhập vào admin console.

Query: `date`, `from`, `to`, `employee_id`, `department`, `status`, `page`, `page_size`.

`status` có thể là:

- `present`
- `late`
- `missing`

Response:

```json
{
  "items": [
    {
      "date": "2026-05-08",
      "employee_id": 1,
      "employee_code": "E001",
      "full_name": "Nguyễn Văn A",
      "department": "IT",
      "first_check_in": "2026-05-08T08:55:00+07:00",
      "last_check_out": "2026-05-08T17:32:00+07:00",
      "summary_status": "present"
    }
  ],
  "total": 1
}
```

### `GET /api/attendance/reports/daily/export.csv`

Yêu cầu đăng nhập vào admin console.

Query giống `GET /api/attendance/reports/daily`.

Response: file CSV UTF-8 BOM.

### `GET /api/attendance/reports/dashboard-summary`

Yêu cầu đăng nhập vào admin console.

Query: `days` chỉ hỗ trợ `7` hoặc `30`.

Response:

```json
{
  "business_timezone": "Asia/Ho_Chi_Minh",
  "total_employees": 10,
  "today": {
    "present": 8,
    "late": 1,
    "absent": 2
  },
  "trend": [
    {
      "date": "2026-05-08",
      "check_in_count": 8
    }
  ]
}
```

### `GET /api/attendance/events`

Yêu cầu đăng nhập vào admin console.

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
        "full_name": "Nguyễn Văn A"
      }
    }
  ],
  "total": 1
}
```

### `GET /api/attendance/events/export.csv`

Yêu cầu đăng nhập vào admin console.

Query: `employee_id`, `action_type`, `from`, `to`.

Response: file CSV UTF-8 BOM.

### `DELETE /api/attendance/events/selected`

Yêu cầu quyền operator (`owner` hoặc `admin`).

```json
{
  "ids": [101, 102]
}
```

Response:

```json
{
  "ok": true,
  "deleted_count": 2
}
```

### `DELETE /api/attendance/events`

Yêu cầu quyền operator (`owner` hoặc `admin`).

Response:

```json
{
  "ok": true,
  "deleted_count": 120
}
```

## Người dùng quản trị

Tất cả endpoint dưới đây đều là owner-only.

### `GET /api/admin/users`

Query: `q`, `page`, `page_size`.

Response:

```json
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "role": "owner",
      "is_active": true,
      "created_at": "2026-05-08T10:00:00Z",
      "updated_at": "2026-05-08T10:00:00Z"
    }
  ],
  "total": 1
}
```

### `POST /api/admin/users`

```json
{
  "username": "viewer-demo",
  "password": "viewer-demo-123",
  "role": "viewer",
  "is_active": true
}
```

### `PUT /api/admin/users/{user_id}`

```json
{
  "username": "ops-admin",
  "role": "admin",
  "is_active": true
}
```

### `POST /api/admin/users/{user_id}/reset-password`

```json
{
  "password": "new-password-123"
}
```

Response:

```json
{
  "ok": true,
  "user": {
    "id": 2,
    "username": "viewer-demo",
    "role": "viewer",
    "is_active": true,
    "created_at": "2026-05-08T10:00:00Z",
    "updated_at": "2026-05-08T10:00:00Z"
  }
}
```

### `DELETE /api/admin/users/{user_id}`

Response:

```json
{
  "ok": true
}
```

## Cấu hình hệ thống

### `GET /api/system/settings`

Yêu cầu đăng nhập vào admin console.

Endpoint này chỉ trả cấu hình không nhạy cảm. Response không chứa secret như `JWT_SECRET_KEY`, `MYSQL_PASSWORD`, `MINIO_SECRET_KEY`.

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
  },
  "fields": [
    {
      "key": "attendance_threshold",
      "value": 0.3,
      "source": "db",
      "editable": true,
      "value_type": "float",
      "requires_restart": false,
      "min_value": 0.0,
      "max_value": 1.0,
      "allowed_values": null
    }
  ]
}
```

### `PATCH /api/system/settings`

Yêu cầu owner.

Chỉ gửi các field cần đổi.

```json
{
  "attendance_threshold": 0.28,
  "business_timezone": "Asia/Ho_Chi_Minh",
  "warmup_face_model": true
}
```

### `POST /api/system/settings/reset`

Yêu cầu owner.

```json
{
  "keys": ["attendance_threshold", "business_timezone"]
}
```

## Healthcheck

### `GET /healthz`

```json
{
  "status": "ok"
}
```
