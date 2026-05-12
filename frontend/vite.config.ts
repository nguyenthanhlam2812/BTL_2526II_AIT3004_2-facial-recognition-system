import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const defaultKioskToken = "local-kiosk-token";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, ".."), "");
  const kioskToken = env.KIOSK_API_TOKEN || defaultKioskToken;

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
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          headers: {
            "X-Kiosk-Token": kioskToken,
          },
        },
        "/api": "http://127.0.0.1:8000",
        "/healthz": "http://127.0.0.1:8000",
      },
    },
  };
});
