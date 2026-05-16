import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Group,
  Image,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from "@mantine/core";
import { Dropzone, IMAGE_MIME_TYPE } from "@mantine/dropzone";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconCamera,
  IconCameraOff,
  IconCheck,
  IconPhoto,
  IconSparkles,
  IconTrash,
  IconUpload,
  IconX,
} from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { createEnrollment, getEnrollmentJob } from "@/shared/api/enrollments";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { canOperate } from "@/shared/lib/access";
import type { Employee } from "@/shared/types/api";
import AccessDeniedState from "@/shared/ui/AccessDeniedState";
import PageHeader from "@/shared/ui/PageHeader";

const MAX_FILES = 5;
const MAX_SIZE_BYTES = 5 * 1024 * 1024;
type EnrollMode = "upload" | "camera";

export default function EnrollPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { state } = useLocation();
  const { user } = useRequireAuth();
  const canMutate = canOperate(user?.role);
  const employee = state?.employee as Employee | undefined;

  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [mode, setMode] = useState<EnrollMode>("upload");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files],
  );

  useEffect(
    () => () => previews.forEach((preview) => URL.revokeObjectURL(preview.url)),
    [previews],
  );

  const stopCamera = useCallback(() => {
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    setCameraStream(null);
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const startCamera = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Trình duyệt không hỗ trợ truy cập camera.");
      return;
    }

    setCameraError(null);
    try {
      stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      cameraStreamRef.current = stream;
      setCameraStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
    } catch {
      setCameraError("Không mở được camera. Hãy kiểm tra quyền truy cập hoặc thiết bị camera.");
      stopCamera();
    }
  }, [stopCamera]);

  const captureFrame = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas || video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
      setCameraError("Camera chưa sẵn sàng để chụp ảnh.");
      return;
    }

    if (files.length >= MAX_FILES) {
      setCameraError(`Chỉ được chọn tối đa ${MAX_FILES} ảnh cho một lần enrollment.`);
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("Không thể tạo ảnh từ camera.");
      return;
    }

    context.save();
    context.translate(canvas.width, 0);
    context.scale(-1, 1);
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    context.restore();

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.92),
    );
    if (!blob) {
      setCameraError("Không thể tạo ảnh JPEG từ camera.");
      return;
    }

    const file = new File([blob], `camera-capture-${formatTimestamp(new Date())}.jpg`, {
      type: "image/jpeg",
    });
    setFiles((prev) => [...prev, file].slice(0, MAX_FILES));
    setCameraError(null);
    notifications.show({
      color: "teal",
      message: "Đã chụp ảnh từ camera.",
    });
  }, [files.length]);

  const handleModeChange = useCallback(
    (value: string) => {
      const nextMode = value as EnrollMode;
      if (nextMode !== "camera") {
        stopCamera();
      }
      setMode(nextMode);
    },
    [stopCamera],
  );

  useEffect(
    () => () => {
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current = null;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    },
    [],
  );

  const { data: jobStatus } = useQuery({
    queryKey: ["enrollment-job", jobId],
    queryFn: () => getEnrollmentJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "success" || status === "failed" ? false : 1500;
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => createEnrollment(Number(id), files),
    onSuccess(data) {
      setJobId(data.job_id);
      stopCamera();
      notifications.show({
        color: "blue",
        message: `Đã upload ${data.uploaded_count} ảnh. Đang xử lý embedding...`,
      });
    },
    onError(err: AxiosError<{ detail?: string }>) {
      notifications.show({
        color: "red",
        title: "Upload thất bại",
        message: err.response?.data?.detail ?? "Có lỗi xảy ra, vui lòng thử lại.",
      });
    },
  });

  const isDone = jobStatus?.status === "success" || jobStatus?.status === "failed";
  const statusColor =
    jobStatus?.status === "success" ? "teal" : jobStatus?.status === "failed" ? "red" : "blue";
  const statusLabel =
    jobStatus?.status === "success"
      ? "Thành công"
      : jobStatus?.status === "failed"
        ? "Thất bại"
        : "Đang xử lý";

  if (!canMutate) {
    return (
      <AccessDeniedState
        title="Không đủ quyền thao tác"
        message="Tài khoản viewer chỉ được xem dữ liệu. Enrollment chỉ dành cho owner hoặc admin."
        onAction={() => navigate("/admin/employees")}
      />
    );
  }

  return (
    <Stack gap="lg" maw={720}>
      <PageHeader
        title={`Enrollment ${employee ? `- ${employee.full_name}` : `#${id}`}`}
        subtitle={
          employee
            ? `${employee.employee_code} - ${employee.department} - ${employee.position}`
            : "Upload ảnh chân dung rõ mặt để tạo embedding nhận diện."
        }
        actions={
          <Button
            variant="subtle"
            leftSection={<IconArrowLeft size={17} />}
            onClick={() => navigate("/admin/employees")}
          >
            Quay lại
          </Button>
        }
      />

      {!jobId && (
        <Paper
          withBorder
          p={{ base: "lg", sm: "xl" }}
          style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
        >
          <Stack gap="lg">
            <Text size="sm" c="var(--text-secondary)">
              Chọn 1-5 ảnh chân dung rõ nét hoặc chụp trực tiếp bằng camera. Ảnh tốt nhất: mặt
              thẳng, đủ ánh sáng, chỉ một người trong khung.
            </Text>

            <SegmentedControl
              value={mode}
              onChange={handleModeChange}
              data={[
                { label: "Upload ảnh", value: "upload" },
                { label: "Camera", value: "camera" },
              ]}
              radius="xl"
              fullWidth
            />

            {mode === "upload" && (
              <Dropzone
                onDrop={(dropped) => setFiles((prev) => [...prev, ...dropped].slice(0, MAX_FILES))}
                onReject={() =>
                  notifications.show({
                    color: "red",
                    message: "File không hợp lệ. Chỉ nhận JPEG/PNG, tối đa 5MB/ảnh.",
                  })
                }
                maxSize={MAX_SIZE_BYTES}
                accept={IMAGE_MIME_TYPE}
                maxFiles={Math.max(MAX_FILES - files.length, 0)}
                disabled={files.length >= MAX_FILES}
                radius="xl"
                p="xl"
                style={{
                  border: "1px dashed rgba(124,92,255,0.45)",
                  background: "rgba(124,92,255,0.045)",
                  boxShadow: files.length ? "0 0 34px rgba(124,92,255,0.1)" : "none",
                }}
              >
                <Stack align="center" gap="sm" py="lg" style={{ pointerEvents: "none" }}>
                  <ThemeIcon size={50} radius={16} variant="light" color="brand">
                    <IconUpload size={26} stroke={1.7} />
                  </ThemeIcon>
                  <Text size="sm" fw={700}>
                    Kéo thả ảnh vào đây, hoặc click để chọn
                  </Text>
                  <Text size="xs" c="var(--text-muted)">
                    {files.length}/{MAX_FILES} ảnh đã chọn - JPEG/PNG - tối đa 5MB/ảnh
                  </Text>
                </Stack>
              </Dropzone>
            )}

            {mode === "camera" && (
              <Stack gap="md">
                <Box
                  style={{
                    position: "relative",
                    overflow: "hidden",
                    aspectRatio: "16 / 10",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 18,
                    background: "rgba(255,255,255,0.025)",
                  }}
                >
                  <video
                    ref={videoRef}
                    muted
                    playsInline
                    style={{
                      width: "100%",
                      height: "100%",
                      display: cameraStream ? "block" : "none",
                      objectFit: "cover",
                      transform: "scaleX(-1)",
                    }}
                  />
                  {!cameraStream && (
                    <Stack
                      align="center"
                      justify="center"
                      gap="sm"
                      h="100%"
                      p="xl"
                      ta="center"
                    >
                      <ThemeIcon size={54} radius={18} variant="light" color="brand">
                        <IconCamera size={28} stroke={1.7} />
                      </ThemeIcon>
                      <Text fw={700}>Camera chưa bật</Text>
                      <Text size="sm" c="var(--text-muted)" maw={360}>
                        Bật camera để chụp ảnh chân dung và đưa ảnh vào danh sách enrollment.
                      </Text>
                    </Stack>
                  )}
                </Box>
                <canvas ref={canvasRef} style={{ display: "none" }} />

                {cameraError && (
                  <Alert color="red" variant="light" title="Camera không sẵn sàng">
                    {cameraError}
                  </Alert>
                )}

                <Group justify="space-between" align="center">
                  <Text size="xs" c="var(--text-muted)">
                    {files.length}/{MAX_FILES} ảnh đã chọn
                  </Text>
                  <Group gap="sm">
                    {cameraStream ? (
                      <Button
                        variant="default"
                        leftSection={<IconCameraOff size={17} />}
                        onClick={stopCamera}
                      >
                        Tắt camera
                      </Button>
                    ) : (
                      <Button
                        variant="default"
                        leftSection={<IconCamera size={17} />}
                        onClick={startCamera}
                      >
                        Bật camera
                      </Button>
                    )}
                    <Button
                      leftSection={<IconPhoto size={17} />}
                      disabled={!cameraStream || files.length >= MAX_FILES}
                      onClick={() => void captureFrame()}
                    >
                      Chụp ảnh
                    </Button>
                  </Group>
                </Group>
              </Stack>
            )}

            {previews.length > 0 && (
              <Stack gap="sm">
                {previews.map((preview, index) => (
                  <Group
                    key={`${preview.file.name}-${index}`}
                    justify="space-between"
                    wrap="nowrap"
                    p="xs"
                    style={{
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 16,
                      background: "rgba(255,255,255,0.025)",
                    }}
                  >
                    <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
                      <Image
                        src={preview.url}
                        alt={preview.file.name}
                        w={54}
                        h={54}
                        radius="md"
                        fit="cover"
                        fallbackSrc=""
                      />
                      <Box style={{ minWidth: 0 }}>
                        <Text size="sm" fw={600} truncate>
                          {preview.file.name}
                        </Text>
                        <Text size="xs" c="var(--text-muted)" className="mono">
                          {(preview.file.size / 1024).toFixed(0)} KB
                        </Text>
                      </Box>
                    </Group>
                    <Tooltip label="Xóa ảnh">
                      <ActionIcon
                        color="red"
                        aria-label="Xóa ảnh"
                        onClick={() => setFiles((prev) => prev.filter((_, i) => i !== index))}
                      >
                        <IconTrash size={17} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                ))}
              </Stack>
            )}

            <Group justify="flex-end">
              <Button variant="default" onClick={() => navigate("/admin/employees")}>
                Hủy
              </Button>
              <Button
                disabled={files.length === 0}
                loading={submitMutation.isPending}
                onClick={() => submitMutation.mutate()}
                leftSection={<IconSparkles size={17} />}
              >
                Upload và Enroll ({files.length} ảnh)
              </Button>
            </Group>
          </Stack>
        </Paper>
      )}

      {jobId && (
        <Paper
          withBorder
          p={{ base: "lg", sm: "xl" }}
          className={!isDone ? "glow-blue" : undefined}
          style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
        >
          <Stack gap="lg">
            <Group justify="space-between">
              <Group gap="sm">
                <ThemeIcon size={42} radius={14} variant="light" color={statusColor}>
                  {jobStatus?.status === "success" ? (
                    <IconCheck size={22} />
                  ) : jobStatus?.status === "failed" ? (
                    <IconX size={22} />
                  ) : (
                    <IconPhoto size={22} />
                  )}
                </ThemeIcon>
                <Stack gap={2}>
                  <Text fw={700}>Trạng thái xử lý</Text>
                  <Text size="xs" c="var(--text-muted)" className="mono">
                    Job {jobId}
                  </Text>
                </Stack>
              </Group>
              <Badge color={statusColor} variant="light" size="lg">
                <Group gap={8} wrap="nowrap">
                  {!isDone && (
                    <span className="pulse-dots">
                      <span />
                      <span />
                      <span />
                    </span>
                  )}
                  {statusLabel}
                </Group>
              </Badge>
            </Group>

            {jobStatus && (
              <Stack gap="sm">
                <Group justify="space-between">
                  <Text size="sm" c="var(--text-secondary)">
                    Ảnh xử lý thành công
                  </Text>
                  <Text fw={700} className="mono">
                    {jobStatus.processed_count}
                  </Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="var(--text-secondary)">
                    Ảnh thất bại
                  </Text>
                  <Text fw={700} className="mono">
                    {jobStatus.failed_count}
                  </Text>
                </Group>
                {jobStatus.message && (
                  <Text size="sm" c="var(--text-secondary)">
                    {jobStatus.message}
                  </Text>
                )}
              </Stack>
            )}

            {isDone && (
              <Group justify="flex-end">
                <Button variant="default" onClick={() => navigate("/admin/employees")}>
                  Về danh sách
                </Button>
                {jobStatus?.status === "success" && (
                  <Button color="teal" onClick={() => navigate("/admin/employees")}>
                    Xong
                  </Button>
                )}
              </Group>
            )}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}

function formatTimestamp(date: Date) {
  const pad = (value: number) => value.toString().padStart(2, "0");
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    "-",
    pad(date.getHours()),
    pad(date.getMinutes()),
    pad(date.getSeconds()),
  ].join("");
}
