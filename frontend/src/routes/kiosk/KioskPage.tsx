import { useRef, useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import dayjs from "dayjs";
import axios from "axios";
import {
  Box,
  Stack,
  Group,
  Title,
  Text,
  Button,
  SegmentedControl,
  Badge,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { postAttendanceFrame } from "@/shared/api/kiosk";
import type { AttendanceActionType, AttendanceFrameResponse } from "@/shared/types/api";

export default function KioskPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [actionType, setActionType] = useState<AttendanceActionType>("check_in");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [result, setResult] = useState<AttendanceFrameResponse | null>(null);

  // Khởi động camera khi mount
  useEffect(() => {
    let stream: MediaStream;
    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
      })
      .then((s) => {
        stream = s;
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => {
        setCameraError("Không truy cập được camera. Vui lòng cấp quyền trong trình duyệt.");
      });

    return () => stream?.getTracks().forEach((t) => t.stop());
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
            if (!blob) { reject(new Error("Không thể chụp ảnh")); return; }
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
      // Tự xoá kết quả sau 4 giây
      setTimeout(() => setResult(null), 4000);
    },
    onError(err: unknown) {
      const message = axios.isAxiosError(err)
        ? err.code === "ECONNABORTED"
          ? "Nhận diện quá lâu. Lần đầu chạy có thể backend đang tải model AI, vui lòng thử lại sau ít phút."
          : err.response?.data?.detail ?? "Lỗi kết nối. Vui lòng thử lại."
        : err instanceof Error
          ? err.message
          : "Lỗi kết nối. Vui lòng thử lại.";
      notifications.show({
        color: "red",
        message,
      });
    },
  });

  return (
    <Box
      style={{
        minHeight: "100vh",
        background: "#111827",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px 16px",
      }}
    >
      <Stack align="center" w="100%" maw={800} gap="lg">
        {/* Header */}
        <Group justify="space-between" w="100%">
          <Title c="white" order={2}>
            Kiosk Chấm Công
          </Title>
          <SegmentedControl
            value={actionType}
            onChange={(v) => setActionType(v as AttendanceActionType)}
            data={[
              { value: "check_in", label: "Check-in" },
              { value: "check_out", label: "Check-out" },
            ]}
            color="teal"
          />
        </Group>

        {/* Khung video */}
        <Box
          style={{
            position: "relative",
            width: "100%",
            borderRadius: 16,
            overflow: "hidden",
            background: "#000",
            minHeight: 200,
          }}
        >
          {cameraError ? (
            <Box
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: 360,
              }}
            >
              <Text c="dimmed" ta="center" px="md">
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
                display: "block",
                transform: "scaleX(-1)", // mirror để nhìn tự nhiên hơn
              }}
            />
          )}

          {/* Overlay kết quả nhận diện */}
          {result && <ResultOverlay result={result} />}
        </Box>

        {/* Canvas ẩn — chỉ dùng để chụp frame */}
        <canvas ref={canvasRef} style={{ display: "none" }} />

        {/* Nút nhận diện */}
        <Button
          size="xl"
          radius="xl"
          w={220}
          color="teal"
          loading={mutation.isPending}
          disabled={!!cameraError || !cameraReady}
          onClick={() => mutation.mutate()}
        >
          Nhận diện
        </Button>

        <ClockText />
      </Stack>
    </Box>
  );
}

/** Overlay hiển thị kết quả phía dưới video */
function ResultOverlay({ result }: { result: AttendanceFrameResponse }) {
  return (
    <Box
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        background: "rgba(0,0,0,0.78)",
        padding: "16px 20px",
        backdropFilter: "blur(6px)",
      }}
    >
      {result.matched ? (
        <Group justify="space-between" align="center">
          <Stack gap={2}>
            <Text c="white" fw={700} size="lg">
              {result.employee?.full_name}
            </Text>
            <Text c="dimmed" size="sm">
              {result.employee?.employee_code} · Điểm: {result.score?.toFixed(3)}
            </Text>
          </Stack>
          <Badge color="green" size="xl" variant="filled">
            ✓ Ghi nhận
          </Badge>
        </Group>
      ) : (
        <Group justify="space-between" align="center">
          <Text c="white" fw={500}>
            {result.message}
          </Text>
          <Badge
            color={result.attendance_status === "multiple_faces" ? "yellow" : "red"}
            size="xl"
            variant="filled"
          >
            {result.attendance_status === "multiple_faces" ? "Nhiều khuôn mặt" : "Không nhận ra"}
          </Badge>
        </Group>
      )}
    </Box>
  );
}

/** Đồng hồ cập nhật mỗi giây */
function ClockText() {
  const [now, setNow] = useState(() => dayjs());
  useEffect(() => {
    const id = setInterval(() => setNow(dayjs()), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <Text c="dimmed" size="sm">
      {now.format("HH:mm:ss — DD/MM/YYYY")}
    </Text>
  );
}
