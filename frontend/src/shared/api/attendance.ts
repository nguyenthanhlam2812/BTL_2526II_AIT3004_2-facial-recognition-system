import { api } from "./client";
import type { AttendanceEventListResponse } from "@/shared/types/api";

export async function listAttendanceEvents(params?: {
  employee_id?: number;
  action_type?: "check_in" | "check_out";
  from?: string; // ISO 8601
  to?: string;   // ISO 8601
  page?: number;
  page_size?: number;
}): Promise<AttendanceEventListResponse> {
  const { data } = await api.get<AttendanceEventListResponse>("/attendance/events", { params });
  return data;
}
