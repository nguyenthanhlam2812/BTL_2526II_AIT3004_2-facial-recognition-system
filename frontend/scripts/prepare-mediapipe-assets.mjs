import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");
const sourceDir = path.join(frontendRoot, "node_modules", "@mediapipe", "tasks-vision", "wasm");
const targetDir = path.join(
  frontendRoot,
  "public",
  "vendor",
  "mediapipe",
  "tasks-vision",
  "wasm",
);

if (!existsSync(sourceDir)) {
  throw new Error(
    "MediaPipe wasm assets are missing. Run 'npm install' in the frontend workspace first.",
  );
}

mkdirSync(targetDir, { recursive: true });

for (const entry of readdirSync(sourceDir)) {
  const sourcePath = path.join(sourceDir, entry);
  if (!statSync(sourcePath).isFile()) {
    continue;
  }

  const targetPath = path.join(targetDir, entry);
  copyFileSync(sourcePath, targetPath);
}
