import { renderHook, waitFor } from "@testing-library/react";
import { useRef } from "react";
import { describe, expect, it } from "vitest";
import { useFaceDetector } from "./useFaceDetector";

function useDetectorWithRef(active: boolean) {
  const videoRef = useRef<HTMLVideoElement>(null);
  return useFaceDetector(videoRef, active);
}

describe("useFaceDetector", () => {
  it("transitions out of the loading state after the detector resolves", async () => {
    const { result } = renderHook(() => useDetectorWithRef(false));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.error).toBeNull();
    expect(result.current.faceDetected).toBe(false);
    expect(result.current.boxes).toEqual([]);
    expect(result.current.faceCount).toBe(0);
  });

  it("does not run detection while `active` is false", async () => {
    const { result } = renderHook(() => useDetectorWithRef(false));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Mocked detector starts with no detections; ensure the state stays empty.
    expect(result.current.boxes).toEqual([]);
    expect(result.current.faceCount).toBe(0);
  });
});
