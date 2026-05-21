import { api } from "./client";
import type { LookupItem, LookupItemListResponse } from "@/shared/types/api";

// ── Departments ─────────────────────────────────────────────────────────

export async function listDepartments(params?: {
  q?: string;
}): Promise<LookupItemListResponse> {
  const { data } = await api.get<LookupItemListResponse>("/departments", { params });
  return data;
}

export async function listDepartmentNames(): Promise<string[]> {
  const { data } = await api.get<string[]>("/departments/names");
  return data;
}

export async function createDepartment(name: string): Promise<LookupItem> {
  const { data } = await api.post<LookupItem>("/departments", { name });
  return data;
}

export async function updateDepartment(id: number, name: string): Promise<LookupItem> {
  const { data } = await api.put<LookupItem>(`/departments/${id}`, { name });
  return data;
}

export async function deleteDepartment(id: number): Promise<{ ok: boolean }> {
  const { data } = await api.delete<{ ok: boolean }>(`/departments/${id}`);
  return data;
}

// ── Positions ───────────────────────────────────────────────────────────

export async function listPositions(params?: {
  q?: string;
}): Promise<LookupItemListResponse> {
  const { data } = await api.get<LookupItemListResponse>("/positions", { params });
  return data;
}

export async function listPositionNames(): Promise<string[]> {
  const { data } = await api.get<string[]>("/positions/names");
  return data;
}

export async function createPosition(name: string): Promise<LookupItem> {
  const { data } = await api.post<LookupItem>("/positions", { name });
  return data;
}

export async function updatePosition(id: number, name: string): Promise<LookupItem> {
  const { data } = await api.put<LookupItem>(`/positions/${id}`, { name });
  return data;
}

export async function deletePosition(id: number): Promise<{ ok: boolean }> {
  const { data } = await api.delete<{ ok: boolean }>(`/positions/${id}`);
  return data;
}
