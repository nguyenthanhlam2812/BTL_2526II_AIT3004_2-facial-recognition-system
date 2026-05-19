import { api } from "./client";
import type {
  AttendanceDashboardSummaryResponse,
  AttendanceDailyReportListResponse,
  AttendanceDailyReportStatus,
  AttendanceEventsDeleteResponse,
  AttendanceEventListResponse,
} from "@/shared/types/api";

export async function listAttendanceEvents(params?: {
  employee_id?: number;
  action_type?: "check_in" | "check_out";
  attendance_status?: "recorded" | "unknown_face" | "multiple_faces";
  from?: string; // ISO 8601
  to?: string;   // ISO 8601
  page?: number;
  page_size?: number;
}): Promise<AttendanceEventListResponse> {
  const { data } = await api.get<AttendanceEventListResponse>("/attendance/events", { params });
  return data;
}

export async function deleteAttendanceEvents(): Promise<AttendanceEventsDeleteResponse> {
  const { data } = await api.delete<AttendanceEventsDeleteResponse>("/attendance/events");
  return data;
}

export async function deleteSelectedAttendanceEvents(
  ids: number[],
): Promise<AttendanceEventsDeleteResponse> {
  const { data } = await api.delete<AttendanceEventsDeleteResponse>("/attendance/events/selected", {
    data: { ids },
  });
  return data;
}

export async function exportAttendanceEventsCsv(params?: {
  employee_id?: number;
  action_type?: "check_in" | "check_out";
  attendance_status?: "recorded" | "unknown_face" | "multiple_faces";
  from?: string;
  to?: string;
}): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get<Blob>("/attendance/events/export.csv", {
    params,
    responseType: "blob",
  });
  const contentDisposition = response.headers["content-disposition"] as string | undefined;
  const filenameMatch = contentDisposition?.match(/filename="?([^"]+)"?/i);
  return {
    blob: response.data,
    filename: filenameMatch?.[1] ?? "attendance-events.csv",
  };
}

export async function listDailyAttendanceReports(params?: {
  date?: string;
  from?: string;
  to?: string;
  employee_id?: number;
  department?: string;
  status?: AttendanceDailyReportStatus;
  page?: number;
  page_size?: number;
}): Promise<AttendanceDailyReportListResponse> {
  const { data } = await api.get<AttendanceDailyReportListResponse>("/attendance/reports/daily", {
    params,
  });
  return data;
}

export async function exportDailyAttendanceReportsCsv(params?: {
  date?: string;
  from?: string;
  to?: string;
  employee_id?: number;
  department?: string;
  status?: AttendanceDailyReportStatus;
}): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get<Blob>("/attendance/reports/daily/export.csv", {
    params,
    responseType: "blob",
  });
  const contentDisposition = response.headers["content-disposition"] as string | undefined;
  const filenameMatch = contentDisposition?.match(/filename="?([^"]+)"?/i);
  return {
    blob: response.data,
    filename: filenameMatch?.[1] ?? "attendance-daily-report.csv",
  };
}

export async function getAttendanceDashboardSummary(params?: {
  days?: 7 | 30;
}): Promise<AttendanceDashboardSummaryResponse> {
  const { data } = await api.get<AttendanceDashboardSummaryResponse>(
    "/attendance/reports/dashboard-summary",
    { params },
  );
  return data;
}
