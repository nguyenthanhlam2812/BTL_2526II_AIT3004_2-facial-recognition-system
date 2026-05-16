import { useEffect, useRef } from "react";
import type { FaceBbox } from "@/shared/hooks/useFaceDetector";

type BboxState = "idle" | "scanning" | "success" | "fail";

type FaceBboxOverlayProps = {
  /** Bounding boxes to render (in display-pixel space). */
  boxes: FaceBbox[];
  /** Current scan state — drives the bbox colour. */
  state: BboxState;
  /** Width of the video element in CSS pixels. */
  width: number;
  /** Height of the video element in CSS pixels. */
  height: number;
};

const COLORS: Record<BboxState, { stroke: string; glow: string }> = {
  idle: {
    stroke: "rgba(124, 92, 255, 0.85)",
    glow: "rgba(124, 92, 255, 0.35)",
  },
  scanning: {
    stroke: "rgba(59, 130, 246, 0.9)",
    glow: "rgba(59, 130, 246, 0.4)",
  },
  success: {
    stroke: "rgba(34, 211, 166, 0.9)",
    glow: "rgba(34, 211, 166, 0.45)",
  },
  fail: {
    stroke: "rgba(255, 85, 119, 0.85)",
    glow: "rgba(255, 85, 119, 0.4)",
  },
};

const CORNER_LEN = 20;
const LINE_WIDTH = 2.5;
const CORNER_RADIUS = 6;
const PADDING = 12;

export default function FaceBboxOverlay({
  boxes,
  state,
  width,
  height,
}: FaceBboxOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    if (boxes.length === 0) return;

    const { stroke, glow } = COLORS[state];

    ctx.strokeStyle = stroke;
    ctx.lineWidth = LINE_WIDTH;
    ctx.lineCap = "round";
    ctx.shadowColor = glow;
    ctx.shadowBlur = 14;

    for (const box of boxes) {
      const x = box.x - PADDING;
      const y = box.y - PADDING;
      const w = box.width + PADDING * 2;
      const h = box.height + PADDING * 2;

      drawCorners(ctx, x, y, w, h);

      // Confidence label
      ctx.shadowBlur = 0;
      ctx.font = "600 11px Inter, system-ui, sans-serif";
      ctx.fillStyle = stroke;
      const label = `${Math.round(box.score * 100)}%`;
      ctx.fillText(label, x + 4, y - 6);
      ctx.shadowBlur = 14;
    }
  }, [boxes, state, width, height]);

  return (
    <canvas
      ref={canvasRef}
      className="face-bbox-canvas"
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}

/** Draw only the four corner brackets of a rectangle — not a full border. */
function drawCorners(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
) {
  const cl = CORNER_LEN;
  const r = CORNER_RADIUS;

  // Top-left
  ctx.beginPath();
  ctx.moveTo(x, y + cl);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.lineTo(x + cl, y);
  ctx.stroke();

  // Top-right
  ctx.beginPath();
  ctx.moveTo(x + w - cl, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + cl);
  ctx.stroke();

  // Bottom-left
  ctx.beginPath();
  ctx.moveTo(x, y + h - cl);
  ctx.lineTo(x, y + h - r);
  ctx.arcTo(x, y + h, x + r, y + h, r);
  ctx.lineTo(x + cl, y + h);
  ctx.stroke();

  // Bottom-right
  ctx.beginPath();
  ctx.moveTo(x + w, y + h - cl);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + w - cl, y + h);
  ctx.stroke();
}
