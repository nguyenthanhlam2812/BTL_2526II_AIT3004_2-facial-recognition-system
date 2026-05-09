import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getToken, getStoredUser } from "@/shared/lib/token";
import type { User } from "@/shared/types/api";

// Guard: redirect về /login nếu chưa có token.
// Trả về { user } từ localStorage để layout hiển thị tên.
export function useRequireAuth(): { user: User | null } {
  const navigate = useNavigate();

  useEffect(() => {
    if (!getToken()) {
      navigate("/login", { replace: true });
    }
  }, [navigate]);

  return { user: getStoredUser() };
}
