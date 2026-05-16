import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActionIcon,
  Box,
  Button,
  Group,
  Image,
  Loader,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconCamera,
  IconCheck,
  IconFaceId,
  IconTrash,
  IconUsers,
} from "@tabler/icons-react";
import { useFaceDetector } from "@/shared/hooks/useFaceDetector";
import FaceBboxOverlay from "@/routes/kiosk/components/FaceBboxOverlay";

// ─── Quality gate thresholds ────────────────────────────────────────────────
/** Mặt phải chiếm ít nhất tỉ lệ này so với chiều rộng hiển thị */
const MIN_FACE_WIDTH_RATIO = 0.2;
/** Tâm mặt không được lệch quá tỉ lệ này so với tâm frame (0 = giữa, 1 = cạnh) */
const MAX_CENTER_OFFSET_RATIO = 0.3;

type QualityStatus =
  | "loading"
  | "detector_error"
  | "no_face"
  | "multiple_faces"
  | "too_small"
  | "off_center"
  | "ok";

type QualityInfo = {
  color: string;
  icon: React.ReactNode;
  label: string;
};

const QUALITY_INFO: Record<QualityStatus, QualityInfo> = {
  loading: {
    color: "gray",
    icon: <Loader size={16} color="gray" />,
    label: "Đang tải bộ phát hiện khuôn mặt...",
  },
  detector_error: {
    color: "red",
    icon: <IconAlertCircle size={16} />,
    label: "Không tải được face detector. Hãy dùng tab Chọn file.",
  },
  no_face: {
    color: "red",
    icon: <IconFaceId size={16} />,
    label: "Không phát hiện khuôn mặt. Nhìn thẳng vào camera.",
  },
  multiple_faces: {
    color: "yellow",
    icon: <IconUsers size={16} />,
    label: "Phát hiện nhiều khuôn mặt. Chỉ 1 người trong khung.",
  },
  too_small: {
    color: "orange",
    icon: <IconFaceId size={16} />,
    label: "Mặt quá nhỏ. Lại gần camera hơn.",
  },
  off_center: {
    color: "orange",
    icon: <IconFaceId size={16} />,
    label: "Mặt lệch khỏi trung tâm. Điều chỉnh vị trí.",
  },
  ok: {
    color: "teal",
    icon: <IconCheck size={16} />,
    label: "Sẵn sàng — Bấm Chụp!",
  },
};

type CapturedShot = {
  file: File;
  url: string;
};

type Props = {
  /** Số ảnh tối đa còn có thể chụp thêm */
  remaining: number;
  onCapture: (file: File) => void;
};

export default function EnrollCameraCapture({ remaining, onCapture }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [videoDims, setVideoDims] = useState({ width: 0, height: 0 });
  const [shots, setShots] = useState<CapturedShot[]>([]);
  const [isCapturing, setIsCapturing] = useState(false);
  const [flashActive, setFlashActive] = useState(false);

  // ── Camera stream ──────────────────────────────────────────────────────────
  useEffect(() => {
    let stream: MediaStream | null = null;

    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
      })
      .then((mediaStream) => {
        stream = mediaStream;
        if (videoRef.current) videoRef.current.srcObject = mediaStream;
      })
      .catch(() => {
        setCameraError("Không truy cập được camera. Vui lòng cấp quyền trong trình duyệt.");
      });

    return () => {
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // Cleanup blob URLs khi component unmount
  useEffect(() => {
    return () => shots.forEach((s) => URL.revokeObjectURL(s.url));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Face detector ──────────────────────────────────────────────────────────
  const faceState = useFaceDetector(videoRef, cameraReady && !cameraError);

  // ── Quality gate ───────────────────────────────────────────────────────────
  const qualityStatus = useMemo<QualityStatus>(() => {
    if (faceState.loading) return "loading";
    if (faceState.error) return "detector_error";
    if (faceState.faceCount === 0) return "no_face";
    if (faceState.faceCount > 1) return "multiple_faces";

    const box = faceState.boxes[0];
    const frameW = videoDims.width;
    const frameH = videoDims.height;

    if (!frameW || !frameH) return "no_face";

    // Kiểm tra kích thước
    if (box.width / frameW < MIN_FACE_WIDTH_RATIO) return "too_small";

    // Kiểm tra vị trí trung tâm
    const faceCenterX = box.x + box.width / 2;
    const faceCenterY = box.y + box.height / 2;
    const offsetX = Math.abs(faceCenterX - frameW / 2) / frameW;
    const offsetY = Math.abs(faceCenterY - frameH / 2) / frameH;
    if (offsetX > MAX_CENTER_OFFSET_RATIO || offsetY > MAX_CENTER_OFFSET_RATIO) {
      return "off_center";
    }

    return "ok";
  }, [faceState, videoDims]);

  const canCapture = qualityStatus === "ok" && remaining > 0 && !isCapturing;

  // Bbox overlay state
  const bboxState = useMemo(() => {
    if (qualityStatus === "ok") return "success" as const;
    if (qualityStatus === "multiple_faces") return "fail" as const;
    if (qualityStatus === "no_face" || qualityStatus === "loading" || qualityStatus === "detector_error")
      return "idle" as const;
    return "fail" as const;
  }, [qualityStatus]);

  // ── Capture ────────────────────────────────────────────────────────────────
  const handleCapture = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !canCapture) return;

    setIsCapturing(true);

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) { setIsCapturing(false); return; }

    // Flip horizontally to match the mirrored display
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);

    // Flash effect
    setFlashActive(true);
    setTimeout(() => setFlashActive(false), 220);

    canvas.toBlob(
      (blob) => {
        if (!blob) { setIsCapturing(false); return; }
        const timestamp = Date.now();
        const file = new File([blob], `enroll_capture_${timestamp}.jpg`, { type: "image/jpeg" });
        const url = URL.createObjectURL(blob);
        setShots((prev) => [...prev, { file, url }]);
        onCapture(file);
        setIsCapturing(false);
      },
      "image/jpeg",
      0.92,
    );
  }, [canCapture, onCapture]);

  const handleRemoveShot = useCallback((index: number) => {
    setShots((prev) => {
      URL.revokeObjectURL(prev[index].url);
      return prev.filter((_, i) => i !== index);
    });
  }, []);

  const qualityInfo = QUALITY_INFO[qualityStatus];

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <Stack gap="md">
      {/* Camera viewport */}
      <Box
        style={{
          position: "relative",
          width: "100%",
          borderRadius: 18,
          overflow: "hidden",
          background: "#000",
          minHeight: 320,
          border: "1px solid rgba(255,255,255,0.08)",
          boxShadow:
            "0 0 0 1px rgba(124,92,255,0.18), 0 24px 70px rgba(0,0,0,0.45), inset 0 0 50px rgba(124,92,255,0.06)",
        }}
      >
        {cameraError ? (
          <Box style={{ minHeight: 320, display: "grid", placeItems: "center", padding: 24 }}>
            <Stack align="center" gap="sm">
              <IconAlertCircle size={36} color="var(--mantine-color-red-5)" />
              <Text c="var(--text-secondary)" ta="center" size="sm">
                {cameraError}
              </Text>
            </Stack>
          </Box>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            onLoadedMetadata={() => {
              setCameraReady(true);
              if (videoRef.current) {
                setVideoDims({
                  width: videoRef.current.clientWidth,
                  height: videoRef.current.clientHeight,
                });
              }
            }}
            onResize={() => {
              if (videoRef.current) {
                setVideoDims({
                  width: videoRef.current.clientWidth,
                  height: videoRef.current.clientHeight,
                });
              }
            }}
            style={{
              width: "100%",
              minHeight: 320,
              display: "block",
              objectFit: "cover",
              transform: "scaleX(-1)",
            }}
          />
        )}

        {/* Bounding box overlay */}
        {cameraReady && videoDims.width > 0 && !faceState.error && (
          <FaceBboxOverlay
            boxes={faceState.boxes}
            state={bboxState}
            width={videoDims.width}
            height={videoDims.height}
          />
        )}

        {/* Center guide oval */}
        {cameraReady && (
          <Box
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: "38%",
              aspectRatio: "3/4",
              border: `2px dashed ${qualityStatus === "ok" ? "rgba(34,211,166,0.55)" : "rgba(255,255,255,0.15)"}`,
              borderRadius: "50%",
              pointerEvents: "none",
              transition: "border-color 250ms ease",
            }}
          />
        )}

        {/* Capture flash effect */}
        {flashActive && (
          <Box
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(255,255,255,0.55)",
              pointerEvents: "none",
              zIndex: 10,
            }}
          />
        )}

        {/* "Hết slot" overlay */}
        {remaining <= 0 && (
          <Box
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(8,10,16,0.72)",
              backdropFilter: "blur(6px)",
              display: "grid",
              placeItems: "center",
              zIndex: 5,
            }}
          >
            <Stack align="center" gap="xs">
              <ThemeIcon size={48} radius={16} variant="light" color="teal">
                <IconCheck size={26} />
              </ThemeIcon>
              <Text fw={700} c="var(--text-primary)">
                Đã chụp đủ số ảnh
              </Text>
              <Text size="sm" c="var(--text-secondary)">
                Bấm "Upload và Enroll" để tiến hành.
              </Text>
            </Stack>
          </Box>
        )}
      </Box>

      {/* Hidden canvas for capture */}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Quality status bar */}
      <Paper
        p="sm"
        radius="lg"
        style={{
          background: `rgba(${
            qualityStatus === "ok"
              ? "34,211,166"
              : qualityStatus === "multiple_faces"
                ? "234,179,8"
                : qualityStatus === "loading"
                  ? "120,120,120"
                  : "239,68,68"
          }, 0.1)`,
          border: `1px solid rgba(${
            qualityStatus === "ok"
              ? "34,211,166"
              : qualityStatus === "multiple_faces"
                ? "234,179,8"
                : qualityStatus === "loading"
                  ? "120,120,120"
                  : "239,68,68"
          }, 0.3)`,
          transition: "all 250ms ease",
        }}
      >
        <Group gap="sm" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
            <ThemeIcon size={32} radius={10} variant="light" color={qualityInfo.color}>
              {qualityInfo.icon}
            </ThemeIcon>
            <Text size="sm" fw={600} c={`var(--mantine-color-${qualityInfo.color}-4)`} style={{ lineHeight: 1.3 }}>
              {qualityInfo.label}
            </Text>
          </Group>

          <Button
            id="enroll-capture-btn"
            leftSection={<IconCamera size={17} />}
            color="teal"
            radius="xl"
            disabled={!canCapture}
            loading={isCapturing}
            onClick={handleCapture}
            style={{ flexShrink: 0 }}
          >
            Chụp ({remaining > 0 ? `còn ${remaining}` : "đủ"})
          </Button>
        </Group>
      </Paper>

      {/* Thumbnail strip */}
      {shots.length > 0 && (
        <Stack gap="xs">
          <Text size="xs" c="var(--text-muted)" fw={600}>
            ẢNH ĐÃ CHỤP ({shots.length})
          </Text>
          <Group gap="sm" wrap="wrap">
            {shots.map((shot, index) => (
              <Box key={shot.url} style={{ position: "relative" }}>
                <Image
                  src={shot.url}
                  w={72}
                  h={72}
                  radius="md"
                  fit="cover"
                  style={{
                    border: "2px solid rgba(34,211,166,0.4)",
                    display: "block",
                  }}
                />
                <Tooltip label="Xóa & chụp lại">
                  <ActionIcon
                    id={`enroll-retake-${index}`}
                    size="xs"
                    color="red"
                    variant="filled"
                    radius="xl"
                    style={{
                      position: "absolute",
                      top: -6,
                      right: -6,
                      zIndex: 2,
                    }}
                    onClick={() => handleRemoveShot(index)}
                  >
                    <IconTrash size={10} />
                  </ActionIcon>
                </Tooltip>
              </Box>
            ))}
          </Group>
        </Stack>
      )}
    </Stack>
  );
}
