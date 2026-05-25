import { api } from "./client";
import type { Employee, EmployeeCreate, EmployeeListResponse } from "@/shared/types/api";

export async function listEmployees(params?: {
  q?: string;
  department?: string;
  page?: number;
  page_size?: number;
}): Promise<EmployeeListResponse> {
  const { data } = await api.get<EmployeeListResponse>("/employees", { params });
  return data;
}

export async function listAllEmployees(): Promise<Employee[]> {
  const pageSize = 100;
  const items: Employee[] = [];
  let page = 1;
  let total = Number.POSITIVE_INFINITY;

  while ((page - 1) * pageSize < total) {
    const response = await listEmployees({ page, page_size: pageSize });
    total = response.total;
    items.push(...response.items);
    if (!response.items.length) {
      break;
    }
    page += 1;
  }

  return items;
}

export async function listEmployeeDepartments(): Promise<string[]> {
  const { data } = await api.get<string[]>("/employees/departments");
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

export async function deleteEmployee(
  id: number,
  options?: { force?: boolean },
): Promise<{ ok: boolean }> {
  const { data } = await api.delete<{ ok: boolean }>(`/employees/${id}`, {
    params: options?.force ? { force: true } : undefined,
  });
  return data;
}
