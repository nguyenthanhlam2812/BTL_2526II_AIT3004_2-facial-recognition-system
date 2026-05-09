import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getToken,
  setToken,
  clearToken,
  getStoredUser,
  setStoredUser,
} from "@/shared/lib/token";
import type { User } from "@/shared/types/api";

export function useAuth() {
  const [user, setUser] = useState<User | null>(() => getStoredUser());
  const navigate = useNavigate();

  function signIn(token: string, u: User) {
    setToken(token);
    setStoredUser(u);
    setUser(u);
  }

  function signOut() {
    clearToken();
    setUser(null);
    navigate("/login", { replace: true });
  }

  return { user, token: getToken(), signIn, signOut };
}
