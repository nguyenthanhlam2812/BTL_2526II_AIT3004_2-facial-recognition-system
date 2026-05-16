// Types bám 1-1 với docs/api-contract.md

export type UserRole = "admin";

export interface User {
  id: number;
  username: string;
  role: UserRole;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

// --- Employee (dùng từ tuần 2) ---
export type EmployeeStatus = "active" | "inactive";

export interface Employee {
  id: number;
  employee_code: string;
  full_name: string;
  department: string;
  position: string;
  status: EmployeeStatus;
  created_at: string;
  updated_at: string;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
}

export interface EmployeeCreate {
  employee_code: string;
  full_name: string;
  department: string;
  position: string;
  status: EmployeeStatus;
}

// --- Enrollment (dùng từ tuần 3) ---
export interface EnrollmentCreateResponse {
  employee_id: number;
  job_id: string;
  status: string;
  uploaded_count: number;
}

export interface EnrollmentStatusResponse {
  job_id: string;
  employee_id: number;
  status: "pending" | "success" | "failed";
  message: string;
  processed_count: number;
  failed_count: number;
}

// --- Attendance (dùng từ tuần 4-5) ---
export type AttendanceActionType = "check_in" | "check_out";
export type AttendanceStatus = "recorded" | "unknown_face" | "multiple_faces";

export interface AttendanceFrameResponse {
  matched: boolean;
  employee: { id: number; employee_code: string; full_name: string } | null;
  score: number | null;
  action_type: AttendanceActionType;
  attendance_status: AttendanceStatus;
  message: string;
  event_id: number;
}

export interface AttendanceEvent {
  id: number;
  created_at: string;
  captured_at: string;
  action_type: AttendanceActionType;
  attendance_status: AttendanceStatus;
  score: number | null;
  camera_id: string | null;
  snapshot_object_key: string | null;
  employee: { id: number; employee_code: string; full_name: string } | null;
}

export interface AttendanceEventListResponse {
  items: AttendanceEvent[];
  total: number;
}

// --- System settings (admin read-only) ---
export interface RedisConnectionInfo {
  scheme: string;
  host: string;
  port: number | null;
  database: number | null;
}

export interface SystemSettingsResponse {
  environment: string;
  api_prefix: string;
  attendance_threshold: number;
  insightface_model_name: string;
  face_min_det_score: number;
  face_min_area_ratio: number;
  face_secondary_area_ratio: number;
  warmup_face_model: boolean;
  qdrant_url: string;
  qdrant_collection_employee_faces: string;
  minio_endpoint: string;
  redis: RedisConnectionInfo;
}
