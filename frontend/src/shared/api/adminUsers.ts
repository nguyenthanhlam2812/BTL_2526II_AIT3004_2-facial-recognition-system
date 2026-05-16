import { api } from "./client";
import type {
  AdminUser,
  AdminUserCreate,
  AdminUserDeleteResponse,
  AdminUserListResponse,
  AdminUserResetPassword,
  AdminUserUpdate,
  AdminUserWriteResponse,
} from "@/shared/types/api";

export async function listAdminUsers(params: {
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<AdminUserListResponse> {
  const { data } = await api.get<AdminUserListResponse>("/admin/users", { params });
  return data;
}

export async function createAdminUser(payload: AdminUserCreate): Promise<AdminUser> {
  const { data } = await api.post<AdminUser>("/admin/users", payload);
  return data;
}

export async function updateAdminUser(id: number, payload: AdminUserUpdate): Promise<AdminUser> {
  const { data } = await api.put<AdminUser>(`/admin/users/${id}`, payload);
  return data;
}

export async function resetAdminUserPassword(
  id: number,
  payload: AdminUserResetPassword,
): Promise<AdminUserWriteResponse> {
  const { data } = await api.post<AdminUserWriteResponse>(
    `/admin/users/${id}/reset-password`,
    payload,
  );
  return data;
}

export async function deleteAdminUser(id: number): Promise<AdminUserDeleteResponse> {
  const { data } = await api.delete<AdminUserDeleteResponse>(`/admin/users/${id}`);
  return data;
}
