import { api } from "./client";
import type {
  SystemSettingsResetRequest,
  SystemSettingsResponse,
  SystemSettingsUpdate,
} from "@/shared/types/api";

export async function getSystemSettings(): Promise<SystemSettingsResponse> {
  const { data } = await api.get<SystemSettingsResponse>("/system/settings");
  return data;
}

export async function updateSystemSettings(
  payload: SystemSettingsUpdate,
): Promise<SystemSettingsResponse> {
  const { data } = await api.patch<SystemSettingsResponse>("/system/settings", payload);
  return data;
}

export async function resetSystemSettings(
  payload: SystemSettingsResetRequest = {},
): Promise<SystemSettingsResponse> {
  const { data } = await api.post<SystemSettingsResponse>("/system/settings/reset", payload);
  return data;
}
