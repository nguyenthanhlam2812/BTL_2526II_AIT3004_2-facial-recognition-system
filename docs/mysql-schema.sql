-- MySQL schema snapshot for ERD rendering tools such as ERDPlus,
-- diagrams.net SQL import plugins, DBeaver, DataGrip, or MySQL Workbench.
-- Source of truth remains the SQLAlchemy models and Alembic migrations.

CREATE TABLE alembic_version (
  version_num VARCHAR(32) NOT NULL,
  PRIMARY KEY (version_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE users (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'owner',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY ix_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE departments (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY ix_departments_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE positions (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY ix_positions_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE employees (
  id INT NOT NULL AUTO_INCREMENT,
  employee_code VARCHAR(32) NOT NULL,
  full_name VARCHAR(255) NOT NULL,
  department VARCHAR(128) NOT NULL,
  position VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY ix_employees_employee_code (employee_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE audit_logs (
  id INT NOT NULL AUTO_INCREMENT,
  actor_user_id INT NULL,
  actor_username VARCHAR(64) NULL,
  actor_role VARCHAR(32) NULL,
  action VARCHAR(64) NOT NULL,
  resource_type VARCHAR(64) NOT NULL,
  resource_id VARCHAR(128) NULL,
  resource_label VARCHAR(255) NULL,
  metadata_json TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_audit_logs_actor_user_id (actor_user_id),
  KEY ix_audit_logs_action (action),
  KEY ix_audit_logs_resource_type (resource_type),
  KEY ix_audit_logs_created_at (created_at),
  CONSTRAINT fk_audit_logs_actor_user_id
    FOREIGN KEY (actor_user_id) REFERENCES users(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE system_settings (
  `key` VARCHAR(128) NOT NULL,
  value TEXT NOT NULL,
  updated_by_user_id INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`key`),
  KEY ix_system_settings_updated_by_user_id (updated_by_user_id),
  CONSTRAINT fk_system_settings_updated_by_user_id
    FOREIGN KEY (updated_by_user_id) REFERENCES users(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE enrollments (
  id INT NOT NULL AUTO_INCREMENT,
  job_id VARCHAR(64) NOT NULL,
  employee_id INT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  uploaded_count INT NOT NULL DEFAULT 0,
  processed_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY ix_enrollments_job_id (job_id),
  KEY ix_enrollments_employee_id (employee_id),
  CONSTRAINT fk_enrollments_employee_id
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE enrollment_images (
  id INT NOT NULL AUTO_INCREMENT,
  enrollment_id INT NOT NULL,
  object_key VARCHAR(512) NOT NULL,
  original_file_name VARCHAR(255) NOT NULL,
  content_type VARCHAR(128) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  processing_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  qdrant_point_id VARCHAR(128) NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_enrollment_images_enrollment_id (enrollment_id),
  CONSTRAINT fk_enrollment_images_enrollment_id
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE attendance_events (
  id INT NOT NULL AUTO_INCREMENT,
  employee_id INT NULL,
  action_type VARCHAR(32) NOT NULL,
  attendance_status VARCHAR(32) NOT NULL,
  score DECIMAL(6, 4) NULL,
  camera_id VARCHAR(128) NULL,
  snapshot_object_key VARCHAR(512) NULL,
  captured_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_attendance_events_employee_id (employee_id),
  KEY ix_attendance_events_action_type (action_type),
  KEY ix_attendance_events_attendance_status (attendance_status),
  CONSTRAINT fk_attendance_events_employee_id
    FOREIGN KEY (employee_id) REFERENCES employees(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Logical, non-FK links:
-- employees.department matches departments.name after backend validation.
-- employees.position matches positions.name after backend validation.
-- enrollment_images.object_key points to MinIO enrollment images.
-- enrollment_images.qdrant_point_id points to Qdrant employee face vectors.
-- attendance_events.snapshot_object_key is reserved for future MinIO snapshots.
