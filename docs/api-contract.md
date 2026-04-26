# API Contract

## Mục đích

Tài liệu này chốt contract API thô để frontend có thể dùng mock và backend có điểm bám khi sang Phase 3.

## Quy ước chung

- Prefix API: `/api`
- Auth: Bearer token cho các route admin
- Định dạng response lỗi:

```json
{
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

## 1. Auth

### `POST /api/auth/login`

Request:

```json
{
  "username": "admin",
  "password": "secret"
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

## 2. Employee

### Metadata employee cho MVP

Business fields cần chốt để frontend và backend cùng bám vào:

- `employee_code`: required, unique
- `full_name`: required
- `department`: required
- `position`: required
- `status`: required, `active` hoặc `inactive`

System fields dự kiến có trong response hoặc DB:

- `id`
- `created_at`
- `updated_at`

Ngoài scope hiện tại, chưa thêm:

- `email`
- `phone`
- `address`
- `shift_code`
- thông tin payroll hoặc HR chi tiết

### `GET /api/employees`

Query:
- `q` optional
- `page` optional
- `page_size` optional

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
      "created_at": "2026-04-23T10:00:00Z",
      "updated_at": "2026-04-23T10:00:00Z"
    }
  ],
  "total": 1
}
```

### `POST /api/employees`

Request:

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

Request: giống `POST /api/employees`

### `DELETE /api/employees/{employee_id}`

Response:

```json
{
  "ok": true
}
```

## 3. Enrollment

### `POST /api/employees/{employee_id}/enrollments`

Content type:
- `multipart/form-data`

Fields:
- `files[]`: 1-5 ảnh

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

Response:

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

## 4. Attendance Recognition

### `POST /api/attendance/frame`

Ghi chú:
- Phase 1 chốt HTTP polling là contract chính.
- WebSocket có thể thêm sau nếu thật sự cần.

Content type:
- `multipart/form-data`

Fields:
- `image`: JPEG frame
- `action_type`: required, `check_in` hoặc `check_out`
- `captured_at`: optional ISO datetime
- `camera_id`: optional

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
  "message": "Check-in recorded",
  "event_id": 101
}
```

Response khi unknown:

```json
{
  "matched": false,
  "employee": null,
  "score": 0.31,
  "action_type": "check_in",
  "attendance_status": "unknown_face",
  "message": "Face not recognized",
  "event_id": 102
}
```

## 5. Attendance History

### `GET /api/attendance/events`

Query:
- `employee_id` optional
- `action_type` optional
- `from` optional
- `to` optional

Response:

```json
{
  "items": [
    {
      "id": 101,
      "created_at": "2026-04-19T10:30:00Z",
      "action_type": "check_in",
      "attendance_status": "recorded",
      "score": 0.86,
      "employee": {
        "id": 1,
        "employee_code": "E001",
        "full_name": "Nguyen Van A"
      },
      "snapshot_url": null
    }
  ],
  "total": 1
}
```

## 6. Healthcheck

### `GET /healthz`

Response:

```json
{
  "status": "ok"
}
```
