// Types bám 1-1 với docs/api-contract.md

export type UserRole = "owner" | "admin" | "viewer";

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

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ChangePasswordResponse {
  ok: boolean;
  message: string;
}

export interface AdminUser {
  id: number;
  username: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminUserListResponse {
  items: AdminUser[];
  total: number;
}

export interface AdminUserCreate {
  username: string;
  password: string;
  role: UserRole;
  is_active: boolean;
}

export interface AdminUserUpdate {
  username?: string;
  role?: UserRole;
  is_active?: boolean;
}

export interface AdminUserResetPassword {
  password: string;
}

export interface AdminUserWriteResponse {
  ok: boolean;
  user: AdminUser;
}

export interface AdminUserDeleteResponse {
  ok: boolean;
}

// --- Employee (dùng từ tuần 2) ---
export type EmployeeStatus = "active" | "inactive";
export type EmployeeFaceDataStatus = "missing" | "pending" | "enrolled" | "failed";

export interface Employee {
  id: number;
  employee_code: string;
  full_name: string;
  department: string;
  position: string;
  status: EmployeeStatus;
  face_data_status: EmployeeFaceDataStatus;
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
export type AttendanceDailyReportStatus = "present" | "late" | "missing";

export interface AttendanceFrameResponse {
  matched: boolean;
  employee: { id: number; employee_code: string; full_name: string } | null;
  score: number | null;
  action_type: AttendanceActionType;
  attendance_status: AttendanceStatus;
  message: string;
  event_id: number | null;
}

export interface AttendanceEvent {
  id: number;
  created_at: string;
  captured_at: string | null;
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

export interface AttendanceEventsDeleteResponse {
  ok: boolean;
  deleted_count: number;
}

export interface AttendanceDailyReport {
  date: string;
  employee_id: number;
  employee_code: string;
  full_name: string;
  department: string;
  first_check_in: string | null;
  last_check_out: string | null;
  summary_status: AttendanceDailyReportStatus;
}

export interface AttendanceDailyReportListResponse {
  items: AttendanceDailyReport[];
  total: number;
}

export interface AttendanceDashboardTodaySummary {
  present: number;
  late: number;
  absent: number;
}

export interface AttendanceDashboardTrendPoint {
  date: string;
  check_in_count: number;
}

export interface AttendanceDashboardSummaryResponse {
  business_timezone: string;
  total_employees: number;
  today: AttendanceDashboardTodaySummary;
  trend: AttendanceDashboardTrendPoint[];
}

// --- System settings ---
export interface RedisConnectionInfo {
  scheme: string;
  host: string;
  port: number | null;
  database: number | null;
}

export interface SystemSettingFieldMeta {
  key: string;
  value: number | boolean | string;
  source: "env" | "db";
  editable: boolean;
  value_type: "float" | "boolean" | "enum";
  requires_restart: boolean;
  min_value: number | null;
  max_value: number | null;
  allowed_values: string[] | null;
}

export interface SystemSettingsResponse {
  environment: string;
  api_prefix: string;
  business_timezone: string;
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
  fields: SystemSettingFieldMeta[];
}

export interface SystemSettingsUpdate {
  attendance_threshold?: number;
  face_min_det_score?: number;
  face_min_area_ratio?: number;
  face_secondary_area_ratio?: number;
  business_timezone?: "UTC" | "Asia/Bangkok" | "Asia/Ho_Chi_Minh";
  warmup_face_model?: boolean;
}

export interface SystemSettingsResetRequest {
  keys?: string[] | null;
}

// --- Audit logs ---
export interface AuditLog {
  id: number;
  actor_user_id: number | null;
  actor_username: string | null;
  actor_role: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  resource_label: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
}
