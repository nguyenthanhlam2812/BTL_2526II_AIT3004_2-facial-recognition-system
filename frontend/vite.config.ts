/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

const defaultKioskToken = "local-kiosk-token";
const rootDir = path.resolve(__dirname, "..");

function readEnvFileValue(filePath: string, key: string) {
  if (!fs.existsSync(filePath)) return undefined;

  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const separatorIndex = trimmed.indexOf("=");
    if (separatorIndex === -1) continue;

    const name = trimmed.slice(0, separatorIndex).trim();
    if (name !== key) continue;

    const value = trimmed.slice(separatorIndex + 1).trim();
    return value.replace(/^['"]|['"]$/g, "");
  }

  return undefined;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, rootDir, "");
  const kioskToken =
    env.KIOSK_API_TOKEN ||
    readEnvFileValue(path.join(rootDir, ".env.docker"), "KIOSK_API_TOKEN") ||
    defaultKioskToken;
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
