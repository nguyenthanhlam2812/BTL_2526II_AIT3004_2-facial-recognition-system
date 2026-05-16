import type { UserRole } from "@/shared/types/api";

export function canOperate(role: UserRole | null | undefined): boolean {
  return role === "owner" || role === "admin";
}

export function isOwner(role: UserRole | null | undefined): boolean {
  return role === "owner";
}
