import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import dayjs from "dayjs";
import axios from "axios";
import {
  Avatar,
  Badge,
  Box,
  Button,
  Group,
  Paper,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconClock, IconLogin2, IconLogout2, IconScan } from "@tabler/icons-react";
import { postAttendanceFrame } from "@/shared/api/kiosk";
import type { AttendanceActionType, AttendanceFrameResponse } from "@/shared/types/api";
import GlowDot from "@/shared/ui/GlowDot";
import ScanFrame from "@/routes/kiosk/components/ScanFrame";
import FaceBboxOverlay from "@/routes/kiosk/components/FaceBboxOverlay";
import { useFaceDetector } from "@/routes/kiosk/hooks/useFaceDetector";

type ScanSource = "auto" | "manual";

type ScanRequest = {
  source: ScanSource;
  recordUnmatched: boolean;
};

const AUTO_SCAN_INTERVAL_MS = 1600;
const AUTO_EMPTY_COOLDOWN_MS = 1200;
const AUTO_MATCHED_COOLDOWN_MS = 10000;
const AUTO_UNMATCHED_COOLDOWN_MS = 3500;
const HEALTHCHECK_TIMEOUT_MS = 3000;
const HEALTHCHECK_RETRY_INTERVAL_MS = 5000;
const RESULT_VISIBLE_MS = 4000;

export default function KioskPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const autoCooldownUntilRef = useRef(0);
  const resultTimerRef = useRef<number | null>(null);
  const [actionType, setActionType] = useState<AttendanceActionType>("check_in");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [isOnline, setIsOnline] = useState(() => window.navigator.onLine);
  const [serverUnavailable, setServerUnavailable] = useState(false);
  const [autoScanEnabled, setAutoScanEnabled] = useState(true);
  const [result, setResult] = useState<AttendanceFrameResponse | null>(null);
  const [videoDims, setVideoDims] = useState({ width: 0, height: 0 });

  const faceState = useFaceDetector(videoRef, cameraReady && !cameraError);
  const detectorUnavailable = Boolean(faceState.error);
  const isDisconnected = !isOnline || serverUnavailable;

  const clearDisplayedResult = useCallback(() => {
    if (resultTimerRef.current) {
      window.clearTimeout(resultTimerRef.current);
      resultTimerRef.current = null;
    }
    setResult(null);
  }, []);

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

    return () => stream?.getTracks().forEach((track) => track.stop());
  }, []);

  useEffect(() => {
    function handleOnline() {
      setIsOnline(true);
    }

    function handleOffline() {
      autoCooldownUntilRef.current = 0;
      clearDisplayedResult();
      setIsOnline(false);
    }

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [clearDisplayedResult]);

  useEffect(() => {
    return () => {
      if (resultTimerRef.current) {
        window.clearTimeout(resultTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    // Only run the probe loop while we are online AND we believe the server
    // is down. The condition reads "early return when not(online && unavailable)"
    // — De Morgan's law applied to the two boolean flags, NOT a bug.
    if (!isOnline || !serverUnavailable) {
      return;
    }

    let cancelled = false;

    const probe = async () => {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), HEALTHCHECK_TIMEOUT_MS);

      try {
        const response = await fetch("/healthz", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!cancelled && response.ok) {
          setServerUnavailable(false);
        }
      } catch {
        // Keep polling until the backend is reachable again.
      } finally {
        window.clearTimeout(timeoutId);
      }
    };

    void probe();
    const intervalId = window.setInterval(() => {
      void probe();
    }, HEALTHCHECK_RETRY_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [isOnline, serverUnavailable]);

  const showResult = useCallback((data: AttendanceFrameResponse) => {
    clearDisplayedResult();
    setResult(data);
    resultTimerRef.current = window.setTimeout(() => setResult(null), RESULT_VISIBLE_MS);
  }, [clearDisplayedResult]);

  const captureFrame = useCallback(
    (recordUnmatched: boolean): Promise<AttendanceFrameResponse> => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || !cameraReady) {
        return Promise.reject(new Error("Camera chưa sẵn sàng"));
      }

      if (!video.videoWidth || !video.videoHeight) {
        return Promise.reject(new Error("Camera chưa có khung hình"));
      }

      const context = canvas.getContext("2d");
      if (!context) {
        return Promise.reject(new Error("Không thể chụp ảnh"));
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0);

      return new Promise((resolve, reject) => {
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error("Không thể chụp ảnh"));
              return;
            }
            postAttendanceFrame(
              blob,
              actionType,
              dayjs().toISOString(),
              "kiosk-web",
              recordUnmatched,
            )
              .then(resolve)
              .catch(reject);
          },
          "image/jpeg",
          0.85,
        );
      });
    },
    [actionType, cameraReady],
  );

  const mutation = useMutation({
    mutationFn: ({ recordUnmatched }: ScanRequest): Promise<AttendanceFrameResponse> =>
      captureFrame(recordUnmatched),
    onSuccess(data, variables) {
      if (variables.source === "auto") {
        if (isNoFaceResult(data)) {
          setResult(null);
          autoCooldownUntilRef.current = Date.now() + AUTO_EMPTY_COOLDOWN_MS;
          return;
        }

        if (data.matched) {
          autoCooldownUntilRef.current = Date.now() + AUTO_MATCHED_COOLDOWN_MS;
        } else {
          autoCooldownUntilRef.current = Date.now() + AUTO_UNMATCHED_COOLDOWN_MS;
        }
      }

      showResult(data);
    },
    onError(err: unknown, variables) {
      if (isConnectivityError(err)) {
        setServerUnavailable(true);
        autoCooldownUntilRef.current = 0;
        clearDisplayedResult();
        return;
      }

      if (variables.source === "auto") {
        autoCooldownUntilRef.current = Date.now() + AUTO_UNMATCHED_COOLDOWN_MS;
        return;
      }

      const message = axios.isAxiosError(err)
        ? err.code === "ECONNABORTED"
          ? "Nhận diện quá lâu. Lần đầu chạy có thể backend đang tải model AI, vui lòng thử lại sau ít phút."
          : err.response?.data?.detail ?? "Lỗi kết nối. Vui lòng thử lại."
        : err instanceof Error
          ? err.message
          : "Lỗi kết nối. Vui lòng thử lại.";
      notifications.show({ color: "red", message });
    },
  });

  const { isPending, mutate } = mutation;
  const canScan = cameraReady && !cameraError && !isPending && !isDisconnected;
  const canAutoScan =
    autoScanEnabled &&
    cameraReady &&
    !cameraError &&
    !faceState.loading &&
    !detectorUnavailable &&
    !isDisconnected;

  const triggerScan = useCallback(
    (source: ScanSource) => {
      if (!canScan) return;
      mutate({
        source,
        recordUnmatched: source === "manual",
      });
    },
    [canScan, mutate],
  );

  useEffect(() => {
    if (!canAutoScan) {
      return;
    }

    const intervalId = window.setInterval(() => {
      if (Date.now() < autoCooldownUntilRef.current) {
        return;
      }
      if (!faceState.faceDetected) {
        return;
      }
      triggerScan("auto");
    }, AUTO_SCAN_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [canAutoScan, faceState.faceDetected, triggerScan]);

  const scanState = useMemo(() => {
    if (isPending) return "scanning";
    if (result?.matched) return "success";
    if (result && !result.matched) return "fail";
    return "idle";
  }, [isPending, result]);

  const cameraStatusLabel = useMemo(() => {
    if (!isOnline) return "Mất kết nối mạng";
    if (serverUnavailable) return "Không kết nối được tới máy chủ";
    if (cameraError) return "Camera lỗi";
    if (!cameraReady) return "Đang mở camera";
    if (faceState.loading) return "Đang tải bộ phát hiện khuôn mặt";
    if (detectorUnavailable) return "Tự động quét không khả dụng, vui lòng quét thủ công";
    if (isPending) return "Đang quét";
    return canAutoScan ? "Tự động quét sẵn sàng" : "Camera sẵn sàng";
  }, [
    cameraError,
    cameraReady,
    canAutoScan,
    detectorUnavailable,
    faceState.loading,
    isOnline,
    isPending,
    serverUnavailable,
  ]);

  const cameraStatus = useMemo(() => {
    if (isDisconnected) return "danger";
    if (cameraError) return "danger";
    if (!cameraReady || faceState.loading || detectorUnavailable) return "warning";
    return "success";
  }, [cameraError, cameraReady, detectorUnavailable, faceState.loading, isDisconnected]);

  return (
    <Box
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "28px 16px",
        background:
          "radial-gradient(circle at 18% 10%, rgba(124,92,255,0.22), transparent 30rem), radial-gradient(circle at 85% 78%, rgba(59,130,246,0.16), transparent 28rem), var(--bg-base)",
      }}
    >
      <Stack w="100%" maw={980} gap="lg">
        <Group justify="space-between" align="center" wrap="wrap">
          <Stack gap={4}>
            <Group gap="sm">
              <ThemeIcon size={42} radius={14} variant="light" color="brand" className="glow-purple">
                <IconScan size={23} stroke={1.8} />
              </ThemeIcon>
              <Title order={1} size="h2" c="var(--text-primary)">
                Kiosk chấm công dùng chung
              </Title>
            </Group>
            <Group gap="sm">
              <GlowDot status={cameraStatus} />
              <Text size="sm" c="var(--text-secondary)">
                {cameraStatusLabel}
              </Text>
            </Group>
          </Stack>

          <SegmentedControl
            value={actionType}
            onChange={(value) => {
              autoCooldownUntilRef.current = 0;
              clearDisplayedResult();
              setActionType(value as AttendanceActionType);
            }}
            data={[
              {
                value: "check_in",
                label: (
                  <Group gap={6} wrap="nowrap">
                    <IconLogin2 size={16} />
                    Check-in
                  </Group>
                ),
              },
              {
                value: "check_out",
                label: (
                  <Group gap={6} wrap="nowrap">
                    <IconLogout2 size={16} />
                    Check-out
                  </Group>
                ),
              },
            ]}
          />
        </Group>

        <Box
          style={{
            position: "relative",
            width: "100%",
            borderRadius: 24,
            overflow: "hidden",
            background: "#000",
            minHeight: 340,
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow:
              "0 0 0 1px rgba(124,92,255,0.18), 0 34px 100px rgba(0,0,0,0.55), inset 0 0 70px rgba(124,92,255,0.08)",
          }}
        >
          {cameraError ? (
            <Box
              style={{
                minHeight: 460,
                display: "grid",
                placeItems: "center",
                padding: 24,
              }}
            >
              <Text c="var(--text-secondary)" ta="center">
                {cameraError}
              </Text>
            </Box>
          ) : (
            <video
              ref={videoRef}
              aria-label="Khung camera kiosk"
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
                minHeight: 460,
                display: "block",
                filter: isDisconnected ? "grayscale(0.35) brightness(0.45)" : "none",
                objectFit: "cover",
                opacity: isDisconnected ? 0.55 : 1,
                transform: "scaleX(-1)",
                transition: "opacity 180ms ease, filter 180ms ease",
              }}
            />
          )}

          {cameraReady && videoDims.width > 0 && !detectorUnavailable && (
            <FaceBboxOverlay
              boxes={faceState.boxes}
              state={scanState}
              width={videoDims.width}
              height={videoDims.height}
            />
          )}
          <ScanFrame active={!cameraError && !isDisconnected} state={scanState} />
          {result && <ResultOverlay result={result} />}
          {isDisconnected && <OfflineOverlay isOnline={isOnline} />}
        </Box>

        <canvas ref={canvasRef} style={{ display: "none" }} />

        <Group justify="space-between" align="center" wrap="wrap">
          <Group gap="lg" align="center" wrap="wrap">
            <ClockText />
            <Stack gap={2}>
              <Switch
                checked={autoScanEnabled}
                disabled={
                  !!cameraError ||
                  !cameraReady ||
                  faceState.loading ||
                  detectorUnavailable ||
                  isDisconnected
                }
                onChange={(event) => {
                  autoCooldownUntilRef.current = 0;
                  clearDisplayedResult();
                  setAutoScanEnabled(event.currentTarget.checked);
                }}
                label="Tự động quét"
              />
              {isDisconnected && (
                <Text size="sm" c="var(--text-secondary)">
                  Kiosk đang tạm dừng quét cho tới khi kết nối ổn định trở lại.
                </Text>
              )}
              {detectorUnavailable && (
                <Text size="sm" c="var(--text-secondary)">
                  Detector khởi tạo thất bại. Hãy dùng nút quét thủ công.
                </Text>
              )}
            </Stack>
          </Group>
          <Button
            size="xl"
            radius="xl"
            w={240}
            variant={canAutoScan ? "light" : "filled"}
            loading={isPending}
            disabled={!canScan}
            onClick={() => triggerScan("manual")}
            leftSection={<IconScan size={22} />}
            className="glow-purple"
          >
            Quét lại ngay
          </Button>
        </Group>
      </Stack>
    </Box>
  );
}

function isNoFaceResult(result: AttendanceFrameResponse) {
  return result.attendance_status === "unknown_face" && result.message === "No face detected.";
}

function ResultOverlay({ result }: { result: AttendanceFrameResponse }) {
  const status =
    result.attendance_status === "multiple_faces"
      ? { color: "yellow", label: "Nhiều khuôn mặt" }
      : result.matched
        ? { color: "teal", label: "Ghi nhận" }
        : { color: "red", label: "Không nhận ra" };

  return (
    <Paper
      className="glass pop-in"
      p="lg"
      style={{
        position: "absolute",
        right: 24,
        bottom: 24,
        left: 24,
        borderRadius: 22,
      }}
    >
      {result.matched ? (
        <Group justify="space-between" align="center" wrap="wrap">
          <Group gap="md" wrap="nowrap">
            <Avatar size={56} radius="xl" color="brand">
              {result.employee?.full_name?.slice(0, 1).toUpperCase()}
            </Avatar>
            <Stack gap={2}>
              <Text c="var(--text-primary)" fw={800} size="xl">
                {result.employee?.full_name}
              </Text>
              <Text c="var(--text-secondary)" size="sm">
                {result.employee?.employee_code} · Điểm{" "}
                <Text span className="mono">
                  {result.score?.toFixed(3)}
                </Text>
              </Text>
            </Stack>
          </Group>
          <Badge color={status.color} size="xl" variant="filled">
            {status.label}
          </Badge>
        </Group>
      ) : (
        <Group justify="space-between" align="center" wrap="wrap">
          <Stack gap={4}>
            <Text c="var(--text-primary)" fw={700} size="lg">
              {result.message}
            </Text>
            <Text c="var(--text-secondary)" size="sm">
              Vui lòng thử lại với một khuôn mặt rõ trong khung.
            </Text>
          </Stack>
          <Badge color={status.color} size="xl" variant="filled">
            {status.label}
          </Badge>
        </Group>
      )}
    </Paper>
  );
}

function ClockText() {
  const [now, setNow] = useState(() => dayjs());

  useEffect(() => {
    const id = window.setInterval(() => setNow(dayjs()), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <Group gap="xs">
      <IconClock size={20} color="var(--text-muted)" />
      <Text c="var(--text-secondary)" size="24px" className="mono">
        {now.format("HH:mm:ss")}
      </Text>
      <Text c="var(--text-muted)" size="sm">
        {now.format("DD/MM/YYYY")}
      </Text>
    </Group>
  );
}

function OfflineOverlay({ isOnline }: { isOnline: boolean }) {
  return (
    <Paper
      p="xl"
      radius={0}
      style={{
        position: "absolute",
        inset: 0,
        display: "grid",
        placeItems: "center",
        background: "rgba(8, 10, 16, 0.76)",
        backdropFilter: "blur(8px)",
        zIndex: 4,
      }}
    >
      <Stack align="center" gap="sm" maw={420}>
        <IconAlertTriangle size={42} color="var(--accent-primary-2)" />
        <Text fw={800} size="xl" c="var(--text-primary)" ta="center">
          {isOnline ? "Không kết nối được tới máy chủ" : "Mất kết nối mạng"}
        </Text>
        <Text size="md" c="var(--text-secondary)" ta="center">
          Mất kết nối mạng, vui lòng kiểm tra lại đường truyền...
        </Text>
      </Stack>
    </Paper>
  );
}

function isConnectivityError(error: unknown) {
  if (!axios.isAxiosError(error)) {
    return false;
  }

  if (error.code === "ERR_NETWORK" || error.code === "ECONNABORTED") {
    return true;
  }

  const status = error.response?.status ?? 0;
  return status >= 500 && status <= 599;
}
