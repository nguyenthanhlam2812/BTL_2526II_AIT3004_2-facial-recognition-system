import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearToken, getToken, isTokenExpired, setToken } from "./token";

function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload)).replace(/=+$/, "");
  return `${header}.${body}.signature`;
}

describe("token utilities", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-17T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
  });

  describe("isTokenExpired", () => {
    it("returns false for a token that expires far in the future", () => {
      const token = makeJwt({ exp: Math.floor(Date.now() / 1000) + 3600 });
      expect(isTokenExpired(token)).toBe(false);
    });

    it("returns true for an expired token", () => {
      const token = makeJwt({ exp: Math.floor(Date.now() / 1000) - 60 });
      expect(isTokenExpired(token)).toBe(true);
    });

    it("returns true for tokens inside the expiry skew window", () => {
      const token = makeJwt({ exp: Math.floor(Date.now() / 1000) + 5 });
      expect(isTokenExpired(token)).toBe(true);
    });

    it("returns true for malformed tokens", () => {
      expect(isTokenExpired("")).toBe(true);
      expect(isTokenExpired("not-a-jwt")).toBe(true);
      expect(isTokenExpired("only.two")).toBe(true);
      expect(isTokenExpired("a.b.c")).toBe(true);
    });

    it("returns true when exp claim is missing", () => {
      const token = makeJwt({ sub: "user" });
      expect(isTokenExpired(token)).toBe(true);
    });
  });

  describe("getToken", () => {
    it("returns the token when still valid", () => {
      const token = makeJwt({ exp: Math.floor(Date.now() / 1000) + 3600 });
      setToken(token);
      expect(getToken()).toBe(token);
    });

    it("returns null and clears storage when token is expired", () => {
      const token = makeJwt({ exp: Math.floor(Date.now() / 1000) - 1 });
      localStorage.setItem("face_attendance_token", token);
      localStorage.setItem("face_attendance_user", '{"id":1}');
      expect(getToken()).toBeNull();
      expect(localStorage.getItem("face_attendance_token")).toBeNull();
      expect(localStorage.getItem("face_attendance_user")).toBeNull();
    });

    it("returns null when no token is stored", () => {
      expect(getToken()).toBeNull();
    });
  });

  describe("clearToken", () => {
    it("removes both token and user keys", () => {
      localStorage.setItem("face_attendance_token", "x");
      localStorage.setItem("face_attendance_user", '{"id":1}');
      clearToken();
      expect(localStorage.getItem("face_attendance_token")).toBeNull();
      expect(localStorage.getItem("face_attendance_user")).toBeNull();
    });
  });
});
