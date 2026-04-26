# Diagrams

## 1. System Architecture

```mermaid
flowchart LR
    Admin["Admin UI (/admin)"]
    Kiosk["Kiosk UI (/kiosk)"]
    Nginx["nginx"]
    Backend["FastAPI backend"]
    Worker["RQ worker"]
    Redis["Redis / RQ queue"]
    MySQL["MySQL"]
    MinIO["MinIO"]
    Qdrant["Qdrant"]
    Camera["Webcam"]

    Admin --> Nginx
    Kiosk --> Nginx
    Camera --> Kiosk
    Nginx --> Backend
    Backend --> MySQL
    Backend --> MinIO
    Backend --> Qdrant
    Backend --> Redis
    Redis --> Worker
    Worker --> MinIO
    Worker --> Qdrant
    Worker --> MySQL
```

## 2. Enrollment Flow

```mermaid
sequenceDiagram
    participant Admin as Admin UI
    participant Backend as FastAPI backend
    participant MinIO as MinIO
    participant MySQL as MySQL
    participant Redis as Redis / RQ
    participant Worker as Worker
    participant Qdrant as Qdrant

    Admin->>Backend: Create employee
    Backend->>MySQL: Insert employee
    Admin->>Backend: Upload 3-5 face images
    Backend->>MinIO: Store enrollment images
    Backend->>MySQL: Create enrollment record
    Backend->>Redis: Enqueue embedding job
    Redis->>Worker: Deliver job
    Worker->>MinIO: Read enrollment images
    Worker->>Worker: Detect face + extract embedding
    Worker->>Qdrant: Upsert embedding vectors
    Worker->>MySQL: Update enrollment status
    Backend-->>Admin: Return job status
```

## 3. Attendance Recognition Flow

```mermaid
sequenceDiagram
    participant Kiosk as Kiosk UI
    participant Backend as FastAPI backend
    participant Qdrant as Qdrant
    participant MySQL as MySQL
    participant MinIO as MinIO

    Kiosk->>Backend: POST /api/attendance/frame (image, action_type)
    Backend->>Backend: Detect face + extract embedding
    Backend->>Qdrant: Search nearest embedding
    Backend->>Backend: Apply cosine threshold

    alt Face matched
        Backend->>MySQL: Insert attendance event
        Backend-->>Kiosk: matched=true, attendance_status=recorded
    else Unknown face
        Backend->>MinIO: Optionally store snapshot
        Backend->>MySQL: Insert unknown event
        Backend-->>Kiosk: matched=false, attendance_status=unknown_face
    else Multiple faces / invalid frame
        Backend->>MinIO: Optionally store snapshot
        Backend->>MySQL: Insert error event
        Backend-->>Kiosk: matched=false, attendance_status=multiple_faces
    end
```

## 4. ERD Draft Cho MySQL

![ERD MySQL](assets/erd-mysql.svg)

```mermaid
erDiagram
    USERS {
        bigint id PK
        varchar username UK
        varchar password_hash
        varchar role
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    EMPLOYEES {
        bigint id PK
        varchar employee_code UK
        varchar full_name
        varchar department
        varchar position
        varchar status
        datetime created_at
        datetime updated_at
    }

    ENROLLMENTS {
        bigint id PK
        varchar job_id UK
        bigint employee_id FK
        varchar status
        int uploaded_count
        int processed_count
        int failed_count
        text message
        datetime created_at
        datetime updated_at
        datetime completed_at
    }

    ENROLLMENT_IMAGES {
        bigint id PK
        bigint enrollment_id FK
        varchar object_key
        varchar original_file_name
        varchar content_type
        int sort_order
        varchar processing_status
        varchar qdrant_point_id
        text error_message
        datetime created_at
        datetime updated_at
    }

    ATTENDANCE_EVENTS {
        bigint id PK
        bigint employee_id FK
        varchar action_type
        varchar attendance_status
        decimal score
        varchar camera_id
        varchar snapshot_object_key
        datetime captured_at
        datetime created_at
    }

    EMPLOYEES ||--o{ ENROLLMENTS : has
    ENROLLMENTS ||--|{ ENROLLMENT_IMAGES : contains
    EMPLOYEES o|--o{ ATTENDANCE_EVENTS : matches
```

### Ghi chú chốt để bám vào schema

- `users` chỉ phục vụ đăng nhập admin trong MVP. Chưa thêm audit trail như `created_by`, `updated_by`.
- `employees` là thực thể nghiệp vụ chính cho CRUD admin và attendance history.
- `enrollments` đại diện cho 1 lần upload ảnh đăng ký của 1 nhân viên, bám theo `job_id`, `status`, `uploaded_count`, `processed_count`, `failed_count`.
- `enrollment_images` là bảng phụ cần có để lưu metadata của từng ảnh upload vào MinIO. Mỗi record tương ứng 1 file ảnh trong một enrollment.
- Giả định MVP: mỗi `enrollment_image` sau khi xử lý thành công sẽ map tới đúng 1 vector trong Qdrant qua `qdrant_point_id`.
- `attendance_events.employee_id` cho phép `NULL` để lưu các case `unknown_face` hoặc `multiple_faces`.
- `attendance_events.snapshot_object_key` cho phép `NULL`; chỉ dùng khi cần lưu snapshot debug trong MinIO.

### Giá trị enum dự kiến cho MVP

- `employees.status`: `active`, `inactive`
- `enrollments.status`: `pending`, `success`, `failed`
- `enrollment_images.processing_status`: `pending`, `success`, `failed`
- `attendance_events.action_type`: `check_in`, `check_out`
- `attendance_events.attendance_status`: `recorded`, `unknown_face`, `multiple_faces`
