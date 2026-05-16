import { useEffect, useMemo, useRef, useState } from "react";
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
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconClock, IconLogin2, IconLogout2, IconScan } from "@tabler/icons-react";
import { postAttendanceFrame } from "@/shared/api/kiosk";
import type { AttendanceActionType, AttendanceFrameResponse } from "@/shared/types/api";
import GlowDot from "@/shared/ui/GlowDot";
import ScanFrame from "@/routes/kiosk/components/ScanFrame";

export default function KioskPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [actionType, setActionType] = useState<AttendanceActionType>("check_in");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [result, setResult] = useState<AttendanceFrameResponse | null>(null);

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

  const mutation = useMutation({
    mutationFn: (): Promise<AttendanceFrameResponse> => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || !cameraReady) {
        return Promise.reject(new Error("Camera chưa sẵn sàng"));
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d")!.drawImage(video, 0, 0);

      return new Promise((resolve, reject) => {
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error("Không thể chụp ảnh"));
              return;
            }
            postAttendanceFrame(blob, actionType, dayjs().toISOString(), "kiosk-web")
              .then(resolve)
              .catch(reject);
          },
          "image/jpeg",
          0.85,
        );
      });
    },
    onSuccess(data) {
      setResult(data);
      window.setTimeout(() => setResult(null), 4000);
    },
    onError(err: unknown) {
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

  const scanState = useMemo(() => {
    if (mutation.isPending) return "scanning";
    if (result?.matched) return "success";
    if (result && !result.matched) return "fail";
    return "idle";
  }, [mutation.isPending, result]);

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
                Kiosk chấm công
              </Title>
            </Group>
            <Group gap="sm">
              <GlowDot status={cameraReady ? "success" : cameraError ? "danger" : "warning"} />
              <Text size="sm" c="var(--text-secondary)">
                {cameraReady ? "Camera sẵn sàng" : cameraError ? "Camera lỗi" : "Đang mở camera"}
              </Text>
            </Group>
          </Stack>

          <SegmentedControl
            value={actionType}
            onChange={(value) => setActionType(value as AttendanceActionType)}
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
              autoPlay
              muted
              playsInline
              onLoadedMetadata={() => setCameraReady(true)}
              style={{
                width: "100%",
                minHeight: 460,
                display: "block",
                objectFit: "cover",
                transform: "scaleX(-1)",
              }}
            />
          )}

          <ScanFrame active={!cameraError} state={scanState} />
          {result && <ResultOverlay result={result} />}
        </Box>

        <canvas ref={canvasRef} style={{ display: "none" }} />

        <Group justify="space-between" align="center" wrap="wrap">
          <ClockText />
          <Button
            size="xl"
            radius="xl"
            w={240}
            loading={mutation.isPending}
            disabled={!!cameraError || !cameraReady}
            onClick={() => mutation.mutate()}
            leftSection={<IconScan size={22} />}
            className="glow-purple"
          >
            Nhận diện
          </Button>
        </Group>
      </Stack>
    </Box>
  );
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
