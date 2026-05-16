import axios from "axios";
import { clearToken, getToken } from "@/shared/lib/token";

const baseURL = "/api";
const DEFAULT_TIMEOUT_MS = 15000;
const KIOSK_TIMEOUT_MS = 600000;

export const api = axios.create({ baseURL, timeout: DEFAULT_TIMEOUT_MS });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      clearToken();
      if (!location.pathname.startsWith("/login")) {
        location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export const publicApi = axios.create({ baseURL, timeout: KIOSK_TIMEOUT_MS });
