/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const defaultKioskToken = "local-kiosk-token";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, ".."), "");
  const kioskToken = env.KIOSK_API_TOKEN || defaultKioskToken;
  const apiTarget = env.VITE_API_TARGET || "http://127.0.0.1:8000";

  return {
    envDir: "..",
    plugins: [react()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "src") },
    },
    server: {
      port: 5173,
      proxy: {
        "/api/attendance/frame": {
          target: apiTarget,
          changeOrigin: true,
          headers: {
            "X-Kiosk-Token": kioskToken,
          },
        },
        "/api": apiTarget,
        "/healthz": apiTarget,
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      css: false,
      include: ["src/**/*.{test,spec}.{ts,tsx}"],
      restoreMocks: true,
      clearMocks: true,
    },
  };
});
