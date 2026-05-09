import axios from "axios";
import { getToken, clearToken } from "@/shared/lib/token";

// baseURL = "/api" — dev: qua Vite proxy; prod: qua Nginx trong image frontend
const baseURL = "/api";
const DEFAULT_TIMEOUT_MS = 15000;
const KIOSK_TIMEOUT_MS = 180000;

// --- api: dùng cho admin (gắn JWT, redirect 401) ---
export const api = axios.create({ baseURL, timeout: DEFAULT_TIMEOUT_MS });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      if (!location.pathname.startsWith("/login")) {
        location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

// --- publicApi: dùng cho kiosk (không gắn JWT, không redirect) ---
// Sẽ dùng từ tuần 5 khi làm KioskPage
export const publicApi = axios.create({ baseURL, timeout: KIOSK_TIMEOUT_MS });
