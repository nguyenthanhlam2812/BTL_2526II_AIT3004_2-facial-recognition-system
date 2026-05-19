import { api } from "./client";
import type { AuditLogListResponse } from "@/shared/types/api";

export async function listAuditLogs(params?: {
  q?: string;
  action?: string;
  resource_type?: string;
  actor_user_id?: number;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}): Promise<AuditLogListResponse> {
  const { data } = await api.get<AuditLogListResponse>("/audit/logs", { params });
  return data;
}
