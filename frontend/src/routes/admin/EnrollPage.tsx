import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Group,
  Image,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from "@mantine/core";
import { Dropzone, IMAGE_MIME_TYPE } from "@mantine/dropzone";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconCheck,
  IconPhoto,
  IconSparkles,
  IconTrash,
  IconUpload,
  IconX,
} from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { createEnrollment, getEnrollmentJob } from "@/shared/api/enrollments";
import type { Employee } from "@/shared/types/api";
import PageHeader from "@/shared/ui/PageHeader";

const MAX_FILES = 5;
const MAX_SIZE_BYTES = 5 * 1024 * 1024;

export default function EnrollPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { state } = useLocation();
  const employee = state?.employee as Employee | undefined;

  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);

  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files],
  );

  useEffect(() => () => previews.forEach((preview) => URL.revokeObjectURL(preview.url)), [previews]);

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

  return (
    <Stack gap="lg" maw={720}>
      <PageHeader
        title={`Enrollment ${employee ? `· ${employee.full_name}` : `#${id}`}`}
        subtitle={
          employee
            ? `${employee.employee_code} · ${employee.department} · ${employee.position}`
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
              Upload 1-5 ảnh chân dung rõ nét (JPEG/PNG, tối đa 5MB/ảnh). Ảnh tốt nhất:
              mặt thẳng, đủ ánh sáng, chỉ một người trong khung.
            </Text>

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
                  {files.length}/{MAX_FILES} ảnh đã chọn · JPEG/PNG · tối đa 5MB/ảnh
                </Text>
              </Stack>
            </Dropzone>

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
                    <Tooltip label="Xoá ảnh">
                      <ActionIcon
                        color="red"
                        aria-label="Xoá ảnh"
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
                Huỷ
              </Button>
              <Button
                disabled={files.length === 0}
                loading={submitMutation.isPending}
                onClick={() => submitMutation.mutate()}
                leftSection={<IconSparkles size={17} />}
              >
                Upload & Enroll ({files.length} ảnh)
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
