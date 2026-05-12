import { api } from "./client";
import type {
  ChangePasswordRequest,
  ChangePasswordResponse,
  LoginRequest,
  LoginResponse,
} from "@/shared/types/api";

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/auth/login", payload);
  return data;
}

export async function changePassword(
  payload: ChangePasswordRequest,
): Promise<ChangePasswordResponse> {
  const { data } = await api.post<ChangePasswordResponse>("/auth/change-password", payload);
  return data;
}
