import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// MediaPipe Tasks Vision loads WASM that jsdom cannot execute. Provide a
// deterministic stub so detector-dependent hooks and components can mount
// without hitting the network or instantiating the real pipeline.
vi.mock("@mediapipe/tasks-vision", () => {
  const fakeDetector = {
    detectForVideo: vi.fn(() => ({ detections: [] })),
    close: vi.fn(),
  };
  return {
    FilesetResolver: {
      forVisionTasks: vi.fn(async () => ({})),
    },
    FaceDetector: {
      createFromOptions: vi.fn(async () => fakeDetector),
    },
  };
});
