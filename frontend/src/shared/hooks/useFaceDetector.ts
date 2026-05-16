import { useEffect, useRef, useState } from "react";
import {
  FaceDetector,
  FilesetResolver,
  type Detection,
} from "@mediapipe/tasks-vision";

const WASM_BASE_PATH = "/vendor/mediapipe/tasks-vision/wasm";
const MODEL_PATH = "/vendor/mediapipe/models/blaze_face_short_range.tflite";
const MIN_DETECTION_CONFIDENCE = 0.6;

export type FaceBbox = {
  x: number;
  y: number;
  width: number;
  height: number;
  score: number;
};

export type FaceDetectorState = {
  faceDetected: boolean;
  faceCount: number;
  boxes: FaceBbox[];
  loading: boolean;
  error: string | null;
};

export function useFaceDetector(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  active: boolean,
): FaceDetectorState {
  const detectorRef = useRef<FaceDetector | null>(null);
  const rafIdRef = useRef<number>(0);
  const lastVideoTimeRef = useRef<number>(-1);

  const [state, setState] = useState<FaceDetectorState>({
    faceDetected: false,
    faceCount: 0,
    boxes: [],
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks(WASM_BASE_PATH);
        if (cancelled) return;

        const detector = await FaceDetector.createFromOptions(vision, {
          baseOptions: { modelAssetPath: MODEL_PATH },
          runningMode: "VIDEO",
          minDetectionConfidence: MIN_DETECTION_CONFIDENCE,
        });

        if (cancelled) {
          detector.close();
          return;
        }

        detectorRef.current = detector;
        setState((prev) => ({ ...prev, loading: false, error: null }));
      } catch {
        if (!cancelled) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: "Face detector assets could not be loaded.",
          }));
        }
      }
    })();

    return () => {
      cancelled = true;
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = 0;
      }
      detectorRef.current?.close();
      detectorRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!active || state.loading || state.error) {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = 0;
      }
      return;
    }

    const detectFrame = () => {
      const video = videoRef.current;
      const detector = detectorRef.current;

      if (
        !video ||
        !detector ||
        video.readyState < 2 ||
        video.currentTime === lastVideoTimeRef.current
      ) {
        rafIdRef.current = requestAnimationFrame(detectFrame);
        return;
      }

      lastVideoTimeRef.current = video.currentTime;

      let detections: Detection[];
      try {
        detections = detector.detectForVideo(video, performance.now()).detections;
      } catch {
        rafIdRef.current = requestAnimationFrame(detectFrame);
        return;
      }

      const videoWidth = video.videoWidth;
      const videoHeight = video.videoHeight;
      const displayWidth = video.clientWidth;
      const displayHeight = video.clientHeight;

      if (!videoWidth || !videoHeight || !displayWidth || !displayHeight) {
        rafIdRef.current = requestAnimationFrame(detectFrame);
        return;
      }

      const scaleX = displayWidth / videoWidth;
      const scaleY = displayHeight / videoHeight;

      const boxes: FaceBbox[] = detections
        .filter((d) => d.boundingBox)
        .map((d) => {
          const bb = d.boundingBox!;
          const rawX = bb.originX * scaleX;
          const rawW = bb.width * scaleX;

          return {
            x: displayWidth - rawX - rawW,
            y: bb.originY * scaleY,
            width: rawW,
            height: bb.height * scaleY,
            score: d.categories?.[0]?.score ?? 0,
          };
        });

      setState({
        faceDetected: boxes.length > 0,
        faceCount: boxes.length,
        boxes,
        loading: false,
        error: null,
      });

      rafIdRef.current = requestAnimationFrame(detectFrame);
    };

    rafIdRef.current = requestAnimationFrame(detectFrame);

    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = 0;
      }
    };
  }, [active, state.error, state.loading, videoRef]);

  return state;
}
