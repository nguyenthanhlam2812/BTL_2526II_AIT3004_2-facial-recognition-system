# API contract

Base URL khi đi qua Nginx:

```text
http://localhost:8080/api
```

Base URL khi gọi trực tiếp backend:

```text
http://localhost:8000/api
```

Admin APIs dùng Bearer token. Kiosk endpoint dùng `X-Kiosk-Token`; khi gọi qua Nginx token được inject server-side.

## Auth

Ví dụ dưới đây dùng seed local trên DB mới. Với public demo, dùng password đã đổi trong `.env.docker` hoặc trong UI.

### `POST /api/auth/login`

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

Yêu cầu đăng nhập. Mật khẩu mới dài 8-128 ký tự, không có khoảng trắng đầu/cuối, có ít nhất một chữ và một số.

```json
{
  "current_password": "admin123",
  "new_password": "newpass123"
}
```

## Users quản trị

Prefix: `/api/admin/users`. Tất cả endpoint owner-only.

| Method | Path | Ý nghĩa |
| --- | --- | --- |
| `GET` | `/api/admin/users` | List users, query `q`, `page`, `page_size` |
| `POST` | `/api/admin/users` | Tạo user |
| `PUT` | `/api/admin/users/{user_id}` | Sửa username, role, active |
| `POST` | `/api/admin/users/{user_id}/reset-password` | Reset password |
| `DELETE` | `/api/admin/users/{user_id}` | Xóa user |

Create user:

```json
{
  "username": "viewer-demo",
  "password": "viewer123",
  "role": "viewer",
  "is_active": true
}
```

Rules:

- `username`: lowercase, 3-64 ký tự, chữ/số/dot/dash/underscore.
- `password`: cùng rule với change-password.
- `role`: `owner`, `admin`, `viewer`.

## Danh mục phòng ban/chức vụ

Yêu cầu đăng nhập admin console. `owner` và `admin` được tạo/sửa/xóa; `viewer` chỉ xem.

### Departments

| Method | Path | Ý nghĩa |
| --- | --- | --- |
| `GET` | `/api/departments` | List department, query `q` |
| `GET` | `/api/departments/names` | List tên để dùng trong select |
| `POST` | `/api/departments` | Tạo department |
| `PUT` | `/api/departments/{id}` | Sửa department |
| `DELETE` | `/api/departments/{id}` | Xóa department nếu chưa có employee dùng |

### Positions

| Method | Path | Ý nghĩa |
| --- | --- | --- |
| `GET` | `/api/positions` | List position, query `q` |
| `GET` | `/api/positions/names` | List tên để dùng trong select |
| `POST` | `/api/positions` | Tạo position |
| `PUT` | `/api/positions/{id}` | Sửa position |
| `DELETE` | `/api/positions/{id}` | Xóa position nếu chưa có employee dùng |

Request tạo/sửa:

```json
{
  "name": "Software Engineering"
}
```

Response list:

```json
{
  "items": [
    {
      "id": 1,
      "name": "Software Engineering",
      "created_at": "2026-05-08T10:00:00"
    }
  ],
  "total": 1
}
```

## Nhân viên

Prefix: `/api/employees`.

| Method | Path | Quyền | Ý nghĩa |
| --- | --- | --- | --- |
| `GET` | `/api/employees` | owner/admin/viewer | List employees, query `q`, `department`, `page`, `page_size` |
| `GET` | `/api/employees/departments` | owner/admin/viewer | List department đang có trong employees, giữ tương thích UI cũ |
| `POST` | `/api/employees` | owner/admin | Tạo employee |
| `PUT` | `/api/employees/{employee_id}` | owner/admin | Sửa employee |
| `DELETE` | `/api/employees/{employee_id}` | owner/admin | Xóa employee nếu chưa có enrollment/attendance |
| `DELETE` | `/api/employees/{employee_id}?force=true` | owner | Xóa vĩnh viễn: drop embedding khỏi Qdrant, ảnh enrollment khỏi MinIO, ẩn danh lịch sử chấm công (`employee_id` -> NULL) |

Create/update:

```json
{
  "employee_code": "EMP001",
  "full_name": "Nguyen Van A",
  "department": "Software Engineering",
  "position": "Software Engineer",
  "status": "active"
}
```

Rules:

- `employee_code`: normalize uppercase, 2-32 ký tự, chỉ chữ/số/dấu gạch ngang, unique case-insensitive.
- `full_name`: 2-100 ký tự, trim/collapse spaces, chặn `<>{}`.
- `department`: phải tồn tại trong `/api/departments`.
- `position`: phải tồn tại trong `/api/positions`.
- `status`: `active` hoặc `inactive`.

Response item:

```json
{
  "id": 1,
  "employee_code": "EMP001",
  "full_name": "Nguyen Van A",
  "department": "Software Engineering",
  "position": "Software Engineer",
  "status": "active",
  "face_data_status": "enrolled",
  "created_at": "2026-05-08T10:00:00",
  "updated_at": "2026-05-08T10:00:00"
}
```

`face_data_status`: `missing`, `pending`, `enrolled`, `failed`.

## Enrollment

### `POST /api/employees/{employee_id}/enrollments`

Quyền `owner` hoặc `admin`.

Content type: `multipart/form-data`

Fields:

- `files`: 1-5 ảnh JPEG/PNG.

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

Yêu cầu đăng nhập admin console.

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

## Chấm công

### `POST /api/attendance/frame`

Kiosk gửi frame nhận diện. Gọi trực tiếp backend phải có `X-Kiosk-Token`.

Content type: `multipart/form-data`

Fields:

- `image`: JPEG/PNG.
- `action_type`: `check_in` hoặc `check_out`.
- `captured_at`: optional ISO datetime.
- `camera_id`: optional string, mặc định theo service.
- `record_unmatched`: optional boolean.

Response khi ghi nhận:

```json
{
  "matched": true,
  "employee": {
    "id": 1,
    "employee_code": "EMP001",
    "full_name": "Nguyen Van A"
  },
  "score": 0.86,
  "action_type": "check_in",
  "attendance_status": "recorded",
  "message": "Check-in recorded.",
  "event_id": 101
}
```

Response khi lỗi nhận diện:

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

`attendance_status`: `recorded`, `unknown_face`, `multiple_faces`.

### Events

| Method | Path | Quyền | Ý nghĩa |
| --- | --- | --- | --- |
| `GET` | `/api/attendance/events` | owner/admin/viewer | List event |
| `GET` | `/api/attendance/events/export.csv` | owner/admin/viewer | Export CSV |
| `DELETE` | `/api/attendance/events/selected` | owner/admin | Xóa các event đã chọn |
| `DELETE` | `/api/attendance/events` | owner/admin | Xóa toàn bộ event |

Query list/export: `employee_id`, `action_type`, `attendance_status`, `from`, `to`, `page`, `page_size`.

Response list:

```json
{
  "items": [
    {
      "id": 101,
      "created_at": "2026-05-08T10:30:00",
      "captured_at": "2026-05-08T10:30:00",
      "action_type": "check_in",
      "attendance_status": "recorded",
      "score": 0.86,
      "camera_id": "main-kiosk",
      "snapshot_object_key": null,
      "employee": {
        "id": 1,
        "employee_code": "EMP001",
        "full_name": "Nguyen Van A"
      }
    }
  ],
  "total": 1
}
```

### Reports

| Method | Path | Ý nghĩa |
| --- | --- | --- |
| `GET` | `/api/attendance/reports/daily` | Báo cáo ngày (bracketing: chỉ check-in sớm nhất + check-out muộn nhất) |
| `GET` | `/api/attendance/reports/daily/export.csv` | Export báo cáo ngày |
| `GET` | `/api/attendance/reports/sessions` | Báo cáo ngày kiểu pair matching: N session/ngày + total work minutes |
| `GET` | `/api/attendance/reports/dashboard-summary` | Summary cho dashboard |

Daily và sessions query share filter: `date`, `from`, `to`, `employee_id`, `department`, `status`, `page`, `page_size`.

`status`: `present`, `late`, `missing`.

Dashboard query: `days=7` hoặc `days=30`.

`reports/sessions` response shape:

```json
{
  "items": [
    {
      "date": "2026-05-27",
      "employee_id": 1,
      "employee_code": "E001",
      "full_name": "Nguyen Van A",
      "department": "IT",
      "sessions": [
        {
          "check_in_at": "2026-05-27T08:00:00",
          "check_out_at": "2026-05-27T11:30:00",
          "duration_minutes": 210,
          "is_complete": true
        },
        {
          "check_in_at": "2026-05-27T12:30:00",
          "check_out_at": "2026-05-27T17:30:00",
          "duration_minutes": 300,
          "is_complete": true
        }
      ],
      "total_work_minutes": 510,
      "summary_status": "present"
    }
  ],
  "total": 1
}
```

Pair-matching rules:
- Greedy: mỗi check-out ghép với check-in sớm nhất chưa được pair.
- Duplicate check-in khi 1 session đang mở → bỏ qua, giữ check-in sớm nhất.
- Orphan check-out (không có check-in trước) → bỏ qua silently.
- Orphan check-in (không có check-out) → trở thành session incomplete (`is_complete=false`, `duration_minutes=null`).
- Cross-midnight (làm đêm): session thuộc business day của check-in.
- `total_work_minutes` chỉ cộng các session complete.

## System settings

Owner-only.

| Method | Path | Ý nghĩa |
| --- | --- | --- |
| `GET` | `/api/system/settings` | Xem cấu hình runtime không chứa secret |
| `PATCH` | `/api/system/settings` | Sửa field editable |
| `POST` | `/api/system/settings/reset` | Reset các key về default |

Patch example:

```json
{
  "attendance_threshold": 0.28,
  "business_timezone": "Asia/Ho_Chi_Minh",
  "warmup_face_model": true
}
```

Reset một số key về giá trị env/default:

```json
{
  "keys": ["attendance_threshold", "business_timezone", "warmup_face_model"]
}
```

Reset tất cả key editable:

```json
{
  "keys": null
}
```

## Audit logs

### `GET /api/audit/logs`

Owner-only.

Query: `q`, `action`, `resource_type`, `actor_user_id`, `from`, `to`, `page`, `page_size`.

Response:

```json
{
  "items": [
    {
      "id": 1,
      "actor_user_id": 1,
      "actor_username": "admin",
      "actor_role": "owner",
      "action": "employee.create",
      "resource_type": "employee",
      "resource_id": "42",
      "resource_label": "EMP001 - Nguyen Van A",
      "metadata": {
        "employee_code": "EMP001"
      },
      "created_at": "2026-05-08T10:00:00"
    }
  ],
  "total": 1
}
```

Audit metadata không lưu password, token, secret hoặc ảnh gốc.

## Healthcheck

### `GET /healthz`

```json
{
  "status": "ok"
}
```
