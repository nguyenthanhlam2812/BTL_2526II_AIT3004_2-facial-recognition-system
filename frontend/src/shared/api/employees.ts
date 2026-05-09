import { api } from "./client";
import type { Employee, EmployeeCreate, EmployeeListResponse } from "@/shared/types/api";

export async function listEmployees(params?: {
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<EmployeeListResponse> {
  const { data } = await api.get<EmployeeListResponse>("/employees", { params });
  return data;
}

export async function createEmployee(payload: EmployeeCreate): Promise<Employee> {
  const { data } = await api.post<Employee>("/employees", payload);
  return data;
}

export async function updateEmployee(id: number, payload: EmployeeCreate): Promise<Employee> {
  const { data } = await api.put<Employee>(`/employees/${id}`, payload);
  return data;
}

export async function deleteEmployee(id: number): Promise<{ ok: boolean }> {
  const { data } = await api.delete<{ ok: boolean }>(`/employees/${id}`);
  return data;
}
