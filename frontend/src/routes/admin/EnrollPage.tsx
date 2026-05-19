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
  Progress,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  ThemeIcon,
  Tooltip,
} from "@mantine/core";
import { Dropzone, IMAGE_MIME_TYPE } from "@mantine/dropzone";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconArrowRight,
  IconCamera,
  IconCameraOff,
  IconCheck,
  IconPhoto,
  IconRefresh,
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
import FaceBboxOverlay from "@/routes/kiosk/components/FaceBboxOverlay";
import { useFaceDetector, type FaceBbox } from "@/routes/kiosk/hooks/useFaceDetector";

const MAX_FILES = 5;
const MAX_SIZE_BYTES = 5 * 1024 * 1024;
const FACE_MIN_WIDTH_RATIO = 0.3;
const FACE_CENTER_TOLERANCE = 0.25;
const FACE_YAW_FRONT_TOLERANCE = 0.055;
const FACE_YAW_TURN_THRESHOLD = 0.075;
const AUTO_CAPTURE_HOLD_MS = 900;
const AUTO_CAPTURE_TICK_MS = 80;
const AUTO_CAPTURE_COOLDOWN_MS = 650;
type EnrollMode = "upload" | "camera";
type CaptureSource = "manual" | "auto";
type FacePoseDirection = "front" | "left" | "right";

type FaceQualityStatus =
  | "idle"
  | "loading"
  | "error"
  | "no-face"
  | "multi-face"
  | "small-face"
  | "off-center"
  | "wrong-pose"
  | "ready";

type FaceQuality = {
  status: FaceQualityStatus;
  canCapture: boolean;
  message: string;
};

const CAMERA_POSES = [
  {
    key: "front",
    label: "Nhìn thẳng",
    direction: "front",
    instruction: "Nhìn thẳng vào camera, giữ mặt ở giữa khung hình.",
    cue: "Nhìn thẳng",
  },
  {
    key: "left",
    label: "Quay trái",
    direction: "left",
    instruction: "Quay mặt nhẹ sang trái, vẫn giữ khuôn mặt trong khung.",
    cue: "Quay trái",
  },
  {
    key: "right",
    label: "Quay phải",
    direction: "right",
    instruction: "Quay mặt nhẹ sang phải, tránh nghiêng quá xa khỏi camera.",
    cue: "Quay phải",
  },
] as const;

type CameraPoseKey = (typeof CAMERA_POSES)[number]["key"];
type CameraCaptureMap = Partial<Record<CameraPoseKey, File>>;

export default function EnrollPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { state } = useLocation();
  const { user } = useRequireAuth();
  const canMutate = canOperate(user?.role);
  const employee = state?.employee as Employee | undefined;

  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [cameraCaptures, setCameraCaptures] = useState<CameraCaptureMap>({});
  const [activePoseKey, setActivePoseKey] = useState<CameraPoseKey>("front");
  const [jobId, setJobId] = useState<string | null>(null);
  const [mode, setMode] = useState<EnrollMode>("upload");
  const [autoCaptureEnabled, setAutoCaptureEnabled] = useState(true);
  const [autoCaptureProgress, setAutoCaptureProgress] = useState(0);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [videoSize, setVideoSize] = useState({ width: 0, height: 0 });
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const autoReadySinceRef = useRef<number | null>(null);
  const autoCooldownUntilRef = useRef(0);
  const autoCapturingRef = useRef(false);
  const captureFrameRef = useRef<((source?: CaptureSource) => Promise<void>) | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const faceState = useFaceDetector(videoRef, mode === "camera" && !!cameraStream);
  const activePose = useMemo(
    () => CAMERA_POSES.find((pose) => pose.key === activePoseKey) ?? CAMERA_POSES[0],
    [activePoseKey],
  );

  useEffect(() => {
    if (mode !== "camera") {
      return;
    }
    const video = videoRef.current;
    if (!video) return;
    const update = () =>
      setVideoSize({ width: video.clientWidth, height: video.clientHeight });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(video);
    return () => observer.disconnect();
  }, [mode, cameraStream]);

  const faceQuality = useMemo<FaceQuality>(() => {
    if (mode !== "camera" || !cameraStream) {
      return { status: "idle", canCapture: false, message: "Bật camera để bắt đầu." };
    }
    if (faceState.loading) {
      return {
        status: "loading",
        canCapture: false,
        message: "Đang tải mô hình nhận diện...",
      };
    }
    if (faceState.error) {
      return { status: "error", canCapture: false, message: faceState.error };
    }
    if (faceState.faceCount === 0) {
      return {
        status: "no-face",
        canCapture: false,
        message: "Không thấy khuôn mặt — đưa mặt vào khung.",
      };
    }
    if (faceState.faceCount > 1) {
      return {
        status: "multi-face",
        canCapture: false,
        message: `Phát hiện ${faceState.faceCount} khuôn mặt — chỉ cần 1 người trong khung.`,
      };
    }
    const box = faceState.boxes[0];
    if (!box || videoSize.width === 0 || videoSize.height === 0) {
      return {
        status: "loading",
        canCapture: false,
        message: "Đang khởi tạo camera...",
      };
    }
    const widthRatio = box.width / videoSize.width;
    if (widthRatio < FACE_MIN_WIDTH_RATIO) {
      return {
        status: "small-face",
        canCapture: false,
        message: "Mặt hơi nhỏ — tiến gần camera hơn.",
      };
    }
    const centerX = box.x + box.width / 2;
    const centerY = box.y + box.height / 2;
    const offsetX = Math.abs(centerX - videoSize.width / 2) / videoSize.width;
    const offsetY = Math.abs(centerY - videoSize.height / 2) / videoSize.height;
    if (offsetX > FACE_CENTER_TOLERANCE || offsetY > FACE_CENTER_TOLERANCE) {
      return {
        status: "off-center",
        canCapture: false,
        message: "Đưa khuôn mặt vào giữa khung hình.",
      };
    }
    const poseMatch = getPoseMatch(activePose.direction, box);
    if (!poseMatch.matches) {
      return {
        status: "wrong-pose",
        canCapture: false,
        message: poseMatch.message,
      };
    }
    return { status: "ready", canCapture: true, message: "Giữ yên để hệ thống tự chụp." };
  }, [activePose.direction, mode, cameraStream, faceState, videoSize]);

  const overlayState =
    faceQuality.status === "ready"
      ? "success"
      : faceQuality.status === "no-face" ||
          faceQuality.status === "multi-face" ||
          faceQuality.status === "small-face" ||
          faceQuality.status === "off-center" ||
          faceQuality.status === "wrong-pose" ||
          faceQuality.status === "error"
        ? "fail"
        : "idle";

  const uploadPreviews = useMemo(
    () => uploadFiles.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [uploadFiles],
  );
  const cameraPreviews = useMemo(
    () =>
      CAMERA_POSES.map((pose) => {
        const file = cameraCaptures[pose.key];
        return {
          pose,
          file,
          url: file ? URL.createObjectURL(file) : null,
        };
      }),
    [cameraCaptures],
  );
  const cameraEnrollmentFiles = useMemo(
    () =>
      CAMERA_POSES.map((pose) => cameraCaptures[pose.key]).filter(
        (file): file is File => Boolean(file),
      ),
    [cameraCaptures],
  );
  const capturedPoseCount = cameraEnrollmentFiles.length;
  const submitFiles = mode === "camera" ? cameraEnrollmentFiles : uploadFiles;
  const canSubmit =
    mode === "camera" ? capturedPoseCount === CAMERA_POSES.length : uploadFiles.length > 0;
  const activePoseCaptured = Boolean(cameraCaptures[activePoseKey]);

  useEffect(
    () => () => uploadPreviews.forEach((preview) => URL.revokeObjectURL(preview.url)),
    [uploadPreviews],
  );

  useEffect(
    () => () =>
      cameraPreviews.forEach((preview) => {
        if (preview.url) URL.revokeObjectURL(preview.url);
      }),
    [cameraPreviews],
  );

  const stopCamera = useCallback(() => {
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    autoReadySinceRef.current = null;
    autoCooldownUntilRef.current = 0;
    autoCapturingRef.current = false;
    setAutoCaptureProgress(0);
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

  const captureFrame = useCallback(async (source: CaptureSource = "manual") => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas || video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
      setCameraError("Camera chưa sẵn sàng để chụp ảnh.");
      return;
    }

    if (!faceQuality.canCapture) {
      setCameraError(faceQuality.message);
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

    const file = new File([blob], `camera-${activePoseKey}-${formatTimestamp(new Date())}.jpg`, {
      type: "image/jpeg",
    });
    const nextCaptures = { ...cameraCaptures, [activePoseKey]: file };
    const nextPose = CAMERA_POSES.find((pose) => !nextCaptures[pose.key]);
    setCameraCaptures(nextCaptures);
    setActivePoseKey(nextPose?.key ?? activePoseKey);
    setCameraError(null);
    notifications.show({
      color: source === "auto" ? "blue" : "teal",
      message:
        source === "auto"
          ? `Tự động chụp ${activePose.label}.`
          : `Đã chụp tư thế ${activePose.label}.`,
    });
  }, [activePose.label, activePoseKey, cameraCaptures, faceQuality]);

  useEffect(() => {
    captureFrameRef.current = captureFrame;
  }, [captureFrame]);

  const handleModeChange = useCallback(
    (value: string) => {
      const nextMode = value as EnrollMode;
      autoReadySinceRef.current = null;
      autoCooldownUntilRef.current = 0;
      setAutoCaptureProgress(0);
      if (nextMode !== "camera") {
        stopCamera();
      } else {
        const nextPose = CAMERA_POSES.find((pose) => !cameraCaptures[pose.key]);
        setActivePoseKey(nextPose?.key ?? CAMERA_POSES[0].key);
      }
      setMode(nextMode);
    },
    [cameraCaptures, stopCamera],
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
    mutationFn: () => createEnrollment(Number(id), submitFiles),
    onSuccess(data) {
      setJobId(data.job_id);
      stopCamera();
      notifications.show({
        color: "blue",
        message: `Đã upload ${data.uploaded_count} ảnh. Đang xử lý embedding...`,
      });
    },
    onError(err: AxiosError<{ detail?: string }>) {
      const isDuplicateFace = err.response?.status === 409;
      notifications.show({
        color: isDuplicateFace ? "orange" : "red",
        title: isDuplicateFace
          ? "Khuôn mặt đã đăng ký cho người khác"
          : "Upload thất bại",
        message: err.response?.data?.detail ?? "Có lỗi xảy ra, vui lòng thử lại.",
      });
    },
  });

  useEffect(() => {
    if (
      mode !== "camera" ||
      !cameraStream ||
      !autoCaptureEnabled ||
      activePoseCaptured ||
      !faceQuality.canCapture ||
      submitMutation.isPending
    ) {
      autoReadySinceRef.current = null;
      return;
    }

    const intervalId = window.setInterval(() => {
      const now = Date.now();
      if (now < autoCooldownUntilRef.current || autoCapturingRef.current) {
        return;
      }

      if (autoReadySinceRef.current === null) {
        autoReadySinceRef.current = now;
        setAutoCaptureProgress(0);
      }

      const progress = Math.min((now - autoReadySinceRef.current) / AUTO_CAPTURE_HOLD_MS, 1);
      setAutoCaptureProgress(Math.round(progress * 100));

      if (progress < 1) {
        return;
      }

      const capture = captureFrameRef.current;
      if (!capture) {
        return;
      }

      autoCapturingRef.current = true;
      autoCooldownUntilRef.current = now + AUTO_CAPTURE_COOLDOWN_MS;
      void capture("auto").finally(() => {
        autoCapturingRef.current = false;
        autoReadySinceRef.current = null;
        setAutoCaptureProgress(0);
      });
    }, AUTO_CAPTURE_TICK_MS);

    return () => window.clearInterval(intervalId);
  }, [
    activePoseCaptured,
    activePoseKey,
    autoCaptureEnabled,
    cameraStream,
    faceQuality.canCapture,
    mode,
    submitMutation.isPending,
  ]);

  const isDone = jobStatus?.status === "success" || jobStatus?.status === "failed";
  const statusColor =
    jobStatus?.status === "success" ? "teal" : jobStatus?.status === "failed" ? "red" : "blue";
  const statusLabel =
    jobStatus?.status === "success"
      ? "Thành công"
      : jobStatus?.status === "failed"
        ? "Thất bại"
        : "Đang xử lý";
  const visibleAutoCaptureProgress =
    autoCaptureEnabled && faceQuality.canCapture && !activePoseCaptured ? autoCaptureProgress : 0;

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
              Chọn 1-5 ảnh chân dung rõ nét hoặc bật camera để hệ thống tự chụp lần lượt
              các góc nhìn thẳng, trái và phải. Ảnh tốt nhất: mặt đủ sáng, chỉ một người trong khung.
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
                onDrop={(dropped) =>
                  setUploadFiles((prev) => [...prev, ...dropped].slice(0, MAX_FILES))
                }
                onReject={() =>
                  notifications.show({
                    color: "red",
                    message: "File không hợp lệ. Chỉ nhận JPEG/PNG, tối đa 5MB/ảnh.",
                  })
                }
                maxSize={MAX_SIZE_BYTES}
                accept={IMAGE_MIME_TYPE}
                maxFiles={Math.max(MAX_FILES - uploadFiles.length, 0)}
                disabled={uploadFiles.length >= MAX_FILES}
                radius="xl"
                p="xl"
                style={{
                  border: "1px dashed rgba(124,92,255,0.45)",
                  background: "rgba(124,92,255,0.045)",
                  boxShadow: uploadFiles.length ? "0 0 34px rgba(124,92,255,0.1)" : "none",
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
                    {uploadFiles.length}/{MAX_FILES} ảnh đã chọn - JPEG/PNG - tối đa 5MB/ảnh
                  </Text>
                </Stack>
              </Dropzone>
            )}

            {mode === "camera" && (
              <Stack gap="md">
                <Box
                  p="md"
                  style={{
                    border: "1px solid rgba(124,92,255,0.32)",
                    borderRadius: 16,
                    background: "rgba(124,92,255,0.07)",
                  }}
                >
                  <Group justify="space-between" align="flex-start" gap="md">
                    <Stack gap={4} style={{ flex: 1 }}>
                      <Text size="xs" c="var(--text-muted)" className="mono">
                        Đã chụp {capturedPoseCount}/{CAMERA_POSES.length} tư thế
                      </Text>
                      <Text fw={800}>{activePose.label}</Text>
                      <Text size="sm" c="var(--text-secondary)">
                        {activePose.instruction}
                      </Text>
                    </Stack>
                    <Stack gap="xs" align="flex-end">
                      <Badge color={activePoseCaptured ? "teal" : "brand"} variant="light">
                        {activePoseCaptured
                          ? "Đã chụp"
                          : autoCaptureEnabled
                            ? "Tự chụp"
                            : "Thủ công"}
                      </Badge>
                      <Switch
                        size="xs"
                        checked={autoCaptureEnabled}
                        disabled={!cameraStream}
                        onChange={(event) => {
                          autoReadySinceRef.current = null;
                          setAutoCaptureProgress(0);
                          setAutoCaptureEnabled(event.currentTarget.checked);
                        }}
                        label="Tự động"
                      />
                    </Stack>
                  </Group>
                  <Progress
                    value={(capturedPoseCount / CAMERA_POSES.length) * 100}
                    color="brand"
                    radius="xl"
                    mt="md"
                  />
                  {cameraStream && !activePoseCaptured && (
                    <Progress
                      value={visibleAutoCaptureProgress}
                      color={faceQuality.canCapture ? "teal" : "brand"}
                      radius="xl"
                      mt="xs"
                      striped={faceQuality.canCapture}
                      animated={faceQuality.canCapture}
                    />
                  )}
                </Box>

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
                  {cameraStream && videoSize.width > 0 && videoSize.height > 0 && (
                    <Box
                      style={{
                        position: "absolute",
                        inset: 0,
                        pointerEvents: "none",
                      }}
                    >
                      <FaceBboxOverlay
                        boxes={faceState.boxes}
                        state={overlayState}
                        width={videoSize.width}
                        height={videoSize.height}
                      />
                    </Box>
                  )}
                  {cameraStream && (
                    <Box
                      className={`enroll-pose-cue ${faceQuality.canCapture ? "ready" : ""}`}
                    >
                      <ThemeIcon
                        size={44}
                        radius={16}
                        variant="light"
                        color={faceQuality.canCapture ? "teal" : "brand"}
                      >
                        <PoseCueIcon poseKey={activePoseKey} />
                      </ThemeIcon>
                      <Stack gap={2} style={{ minWidth: 0 }}>
                        <Text fw={800} size="sm" c="var(--text-primary)">
                          {activePose.cue}
                        </Text>
                        <Text size="xs" c="var(--text-secondary)" lineClamp={2}>
                          {activePoseCaptured
                            ? "Tư thế này đã có ảnh. Chọn tư thế khác hoặc gửi enrollment."
                            : faceQuality.canCapture
                              ? "Giữ yên, hệ thống đang tự chụp..."
                              : faceQuality.message}
                        </Text>
                      </Stack>
                    </Box>
                  )}
                </Box>
                <canvas ref={canvasRef} style={{ display: "none" }} />

                {cameraStream && (
                  <Group
                    gap="xs"
                    align="center"
                    data-testid="face-quality-status"
                    data-status={faceQuality.status}
                  >
                    <Badge
                      color={
                        faceQuality.status === "ready"
                          ? "teal"
                          : faceQuality.status === "loading" || faceQuality.status === "idle"
                            ? "gray"
                            : "yellow"
                      }
                      variant="light"
                    >
                      {faceQuality.status === "ready" ? "Đạt" : "Chưa đạt"}
                    </Badge>
                    <Text size="sm" c="var(--text-secondary)">
                      {faceQuality.message}
                    </Text>
                  </Group>
                )}

                {cameraError && (
                  <Alert color="red" variant="light" title="Camera không sẵn sàng">
                    {cameraError}
                  </Alert>
                )}

                <Group justify="space-between" align="center">
                  <Text size="xs" c="var(--text-muted)">
                    Tự chụp khi mặt đúng hướng, đủ lớn và giữ ổn định trong khung.
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
                      disabled={!cameraStream || !faceQuality.canCapture}
                      onClick={() => void captureFrame()}
                      data-testid="capture-button"
                    >
                      {cameraCaptures[activePoseKey] ? "Chụp lại" : "Chụp thủ công"}
                    </Button>
                  </Group>
                </Group>

                <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
                  {cameraPreviews.map(({ pose, file, url }) => {
                    const isActive = pose.key === activePoseKey;

                    return (
                      <Stack
                        key={pose.key}
                        gap="xs"
                        p="xs"
                        style={{
                          border: isActive
                            ? "1px solid rgba(124,92,255,0.72)"
                            : "1px solid var(--border-subtle)",
                          borderRadius: 14,
                          background: isActive
                            ? "rgba(124,92,255,0.12)"
                            : "rgba(255,255,255,0.025)",
                        }}
                      >
                        {url ? (
                          <Image
                            src={url}
                            alt={pose.label}
                            h={74}
                            radius="md"
                            fit="cover"
                          />
                        ) : (
                          <Stack
                            align="center"
                            justify="center"
                            h={74}
                            style={{
                              borderRadius: 10,
                              background: "rgba(255,255,255,0.035)",
                            }}
                          >
                            <IconPhoto size={20} color="var(--text-muted)" />
                          </Stack>
                        )}
                        <Text size="xs" fw={700} ta="center" lineClamp={1}>
                          {pose.label}
                        </Text>
                        <Button
                          size="xs"
                          variant={isActive ? "filled" : "light"}
                          color={file ? "teal" : "brand"}
                          leftSection={file ? <IconRefresh size={14} /> : undefined}
                          onClick={() => setActivePoseKey(pose.key)}
                        >
                          {file ? "Chụp lại" : "Chọn"}
                        </Button>
                      </Stack>
                    );
                  })}
                </SimpleGrid>
              </Stack>
            )}

            {mode === "upload" && uploadPreviews.length > 0 && (
              <Stack gap="sm">
                {uploadPreviews.map((preview, index) => (
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
                        onClick={() =>
                          setUploadFiles((prev) => prev.filter((_, i) => i !== index))
                        }
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
                disabled={!canSubmit}
                loading={submitMutation.isPending}
                onClick={() => submitMutation.mutate()}
                leftSection={<IconSparkles size={17} />}
              >
                {mode === "camera"
                  ? `Upload và Enroll (${capturedPoseCount}/${CAMERA_POSES.length} tư thế)`
                  : `Upload và Enroll (${uploadFiles.length} ảnh)`}
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

function PoseCueIcon({ poseKey }: { poseKey: CameraPoseKey }) {
  if (poseKey === "left") {
    return <IconArrowLeft size={23} stroke={1.8} />;
  }

  if (poseKey === "right") {
    return <IconArrowRight size={23} stroke={1.8} />;
  }

  return <IconCamera size={23} stroke={1.8} />;
}

function getPoseMatch(direction: FacePoseDirection, box: FaceBbox) {
  const yaw = estimateFaceYaw(box);

  if (yaw === null) {
    return {
      matches: direction === "front",
      message:
        direction === "front"
          ? "Giữ mặt rõ hơn trong khung."
          : "Giữ mặt rõ và quay chậm để camera đọc được hướng mặt.",
    };
  }

  if (direction === "front") {
    const matches = Math.abs(yaw) <= FACE_YAW_FRONT_TOLERANCE;
    return {
      matches,
      message: matches ? "Giữ yên." : "Nhìn thẳng lại camera.",
    };
  }

  if (direction === "left") {
    const matches = yaw <= -FACE_YAW_TURN_THRESHOLD;
    return {
      matches,
      message: matches ? "Giữ yên." : "Quay mặt thêm sang trái.",
    };
  }

  const matches = yaw >= FACE_YAW_TURN_THRESHOLD;
  return {
    matches,
    message: matches ? "Giữ yên." : "Quay mặt thêm sang phải.",
  };
}

function estimateFaceYaw(box: FaceBbox) {
  const nose = pickFaceKeypoint(box, ["nose", "nosetip"], 2);
  if (!nose || box.width <= 0) {
    return null;
  }

  const rightEye = pickFaceKeypoint(box, ["righteye"], 0);
  const leftEye = pickFaceKeypoint(box, ["lefteye"], 1);
  const anchorX =
    rightEye && leftEye ? (rightEye.x + leftEye.x) / 2 : box.x + box.width / 2;

  return (nose.x - anchorX) / box.width;
}

function pickFaceKeypoint(
  box: FaceBbox,
  labelFragments: string[],
  fallbackIndex: number,
) {
  const byLabel = box.keypoints.find((keypoint) => {
    const label = normalizeKeypointLabel(keypoint.label);
    return labelFragments.some((fragment) => label.includes(fragment));
  });

  return byLabel ?? box.keypoints[fallbackIndex] ?? null;
}

function normalizeKeypointLabel(label: string | undefined) {
  return label?.toLowerCase().replace(/[\s_-]/g, "") ?? "";
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
