import { api } from "./client";
import type { SystemSettingsResponse } from "@/shared/types/api";

export async function getSystemSettings(): Promise<SystemSettingsResponse> {
  const { data } = await api.get<SystemSettingsResponse>("/system/settings");
  return data;
}
