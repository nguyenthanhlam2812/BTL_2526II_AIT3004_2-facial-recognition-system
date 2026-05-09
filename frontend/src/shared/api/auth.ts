import { api } from "./client";
import type { LoginRequest, LoginResponse } from "@/shared/types/api";

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/auth/login", payload);
  return data;
}
