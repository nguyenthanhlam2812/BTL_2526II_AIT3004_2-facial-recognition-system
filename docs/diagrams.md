# Sơ đồ hệ thống

File này là nguồn sơ đồ chính của repo. Các sơ đồ dùng Mermaid để GitHub render trực tiếp và dễ chỉnh khi code thay đổi.

## 1. Use case

```mermaid
flowchart LR
    Owner["Owner"]
    Admin["Admin"]
    Viewer["Viewer"]
    Operator["Người vận hành kiosk"]

    Login["Đăng nhập admin"]
    Dashboard["Xem tổng quan"]
    Lookups["Quản lý phòng ban/chức vụ"]
    Employees["Quản lý nhân viên"]
    Enrollment["Đăng ký khuôn mặt"]
    Attendance["Xem/xóa/lọc lịch sử chấm công"]
    Reports["Xem/export báo cáo"]
    Users["Quản lý tài khoản quản trị"]
    Settings["Cấu hình hệ thống"]
    Audit["Xem nhật ký thao tác"]
    Kiosk["Check-in/check-out bằng kiosk"]

    Owner --> Login
    Admin --> Login
    Viewer --> Login
    Owner --> Dashboard
    Admin --> Dashboard
    Viewer --> Dashboard
    Owner --> Lookups
    Admin --> Lookups
    Owner --> Employees
    Admin --> Employees
    Viewer --> Employees
    Owner --> Enrollment
    Admin --> Enrollment
    Owner --> Attendance
    Admin --> Attendance
    Viewer --> Attendance
    Owner --> Reports
    Admin --> Reports
    Viewer --> Reports
    Owner --> Users
    Owner --> Settings
    Owner --> Audit
    Operator --> Kiosk
```

## 2. Triển khai Docker Compose

```mermaid
flowchart LR
    AdminBrowser["Admin browser"] --> Nginx["nginx"]
    KioskBrowser["Kiosk browser"] --> Nginx
    Nginx -->|"/*"| Frontend["frontend: React static SPA"]
    Nginx -->|"/api/*"| Backend["backend: FastAPI"]
    Nginx -->|"inject X-Kiosk-Token"| Backend

    Backend --> MySQL["mysql"]
    Backend --> Redis["redis"]
    Backend --> MinIO["minio"]
    Backend --> Qdrant["qdrant"]

    Redis --> Worker["worker: RQ"]
    Worker --> MinIO
    Worker --> Qdrant
    Worker --> MySQL

    Ngrok["Ngrok optional"] -.-> Nginx
```

## 3. Luồng đăng ký khuôn mặt

```mermaid
sequenceDiagram
    actor Admin
    participant UI as Admin UI
    participant API as FastAPI
    participant MySQL as MySQL
    participant MinIO as MinIO
    participant Redis as Redis
    participant Worker as RQ Worker
    participant Qdrant as Qdrant

    Admin->>UI: Tạo nhân viên, chọn phòng ban/chức vụ
    UI->>API: POST /api/employees
    API->>MySQL: Insert employee
    API-->>UI: Employee created

    Admin->>UI: Upload ảnh hoặc chụp 3 góc
    UI->>API: POST /api/employees/{id}/enrollments
    API->>MinIO: Lưu ảnh enrollment
    API->>MySQL: Tạo enrollment + enrollment_images
    API->>Redis: Enqueue enrollment job
    API-->>UI: job_id, status pending

    Redis->>Worker: Deliver job
    Worker->>MinIO: Đọc ảnh
    Worker->>Worker: Detect face, tạo embedding
    Worker->>Qdrant: Upsert employee face vectors
    Worker->>MySQL: Cập nhật processed/failed/status
    UI->>API: GET /api/enrollments/{job_id}
    API-->>UI: Trạng thái enrollment
```

## 4. Luồng chấm công

```mermaid
sequenceDiagram
    actor Person as Nhân viên trước camera
    participant Kiosk as Kiosk UI
    participant Nginx as Nginx
    participant API as FastAPI
    participant Qdrant as Qdrant
    participant Redis as Redis
    participant MySQL as MySQL

    Person->>Kiosk: Đưa mặt vào khung
    Kiosk->>Nginx: POST /api/attendance/frame
    Nginx->>API: Forward kèm X-Kiosk-Token
    API->>API: Detect face, tạo embedding

    alt Không có mặt hợp lệ
        API->>MySQL: Ghi event unknown_face nếu được cấu hình
        API-->>Kiosk: unknown_face
    else Nhiều mặt
        API->>MySQL: Ghi event multiple_faces
        API-->>Kiosk: multiple_faces
    else Một mặt
        API->>Qdrant: Search nearest embedding
        API->>API: So sánh threshold và employee active
        alt Match hợp lệ
            API->>Redis: Check camera duplicate gate
            alt Chưa ghi trùng
                API->>MySQL: Insert attendance_event recorded
                API->>Redis: Set gate TTL 5 phút
            else Đã ghi trong cửa sổ gate
                API->>Redis: Refresh gate TTL
            end
            API-->>Kiosk: recorded
        else Không đủ ngưỡng
            API->>MySQL: Ghi event unknown_face
            API-->>Kiosk: unknown_face
        end
    end
```

## 5. ERD

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

    DEPARTMENTS {
        int id PK
        varchar name UK
        datetime created_at
    }

    POSITIONS {
        int id PK
        varchar name UK
        datetime created_at
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

    AUDIT_LOGS {
        bigint id PK
        bigint actor_user_id FK
        varchar actor_username
        varchar actor_role
        varchar action
        varchar resource_type
        varchar resource_id
        varchar resource_label
        text metadata_json
        datetime created_at
    }

    SYSTEM_SETTINGS {
        varchar key PK
        text value
        varchar value_type
        datetime updated_at
    }

    EMPLOYEES ||--o{ ENROLLMENTS : has
    ENROLLMENTS ||--|{ ENROLLMENT_IMAGES : contains
    EMPLOYEES o|--o{ ATTENDANCE_EVENTS : matches
    USERS o|--o{ AUDIT_LOGS : writes
```

Ghi chú: `employees.department` và `employees.position` lưu tên đã chọn từ danh mục. Bản hiện tại không dùng foreign key để giữ dữ liệu báo cáo ổn định nếu tên danh mục thay đổi sau này.

## 6. Luồng CI/CD

```mermaid
flowchart TD
    Push["Push hoặc pull request vào main"]
    BackendTests["Backend tests: pytest"]
    FrontendChecks["Frontend: test, lint, build"]
    ComposeConfig["Docker Compose config check"]
    BuildImages["Build 4 images: backend, worker, frontend, nginx"]
    PushImages["Push Docker Hub khi push main"]
    Smoke["Docker Hub smoke test"]

    Push --> BackendTests
    Push --> FrontendChecks
    Push --> ComposeConfig
    BackendTests --> BuildImages
    FrontendChecks --> BuildImages
    ComposeConfig --> BuildImages
    BuildImages --> PushImages
    PushImages --> Smoke
```

Smoke test kiểm tra healthcheck, login, owner-only settings và kiosk token enforcement.
