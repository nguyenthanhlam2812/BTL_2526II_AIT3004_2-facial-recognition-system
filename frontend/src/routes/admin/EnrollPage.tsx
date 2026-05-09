import { useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Stack,
  Group,
  Title,
  Text,
  Button,
  Paper,
  Badge,
  Progress,
} from "@mantine/core";
import { Dropzone, IMAGE_MIME_TYPE } from "@mantine/dropzone";
import { notifications } from "@mantine/notifications";
import type { AxiosError } from "axios";
import { createEnrollment, getEnrollmentJob } from "@/shared/api/enrollments";
import type { Employee } from "@/shared/types/api";

const MAX_FILES = 5;
const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5MB

export default function EnrollPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { state } = useLocation();
  const employee = state?.employee as Employee | undefined;

  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);

  // Poll trạng thái job sau khi submit
  const { data: jobStatus } = useQuery({
    queryKey: ["enrollment-job", jobId],
    queryFn: () => getEnrollmentJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "success" || s === "failed" ? false : 1500;
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
    jobStatus?.status === "success"
      ? "green"
      : jobStatus?.status === "failed"
      ? "red"
      : "blue";

  const statusLabel =
    jobStatus?.status === "success"
      ? "Thành công"
      : jobStatus?.status === "failed"
      ? "Thất bại"
      : "Đang xử lý...";

  return (
    <Stack p="md" gap="md" maw={600}>
      {/* Header */}
      <Stack gap={2}>
        <Title order={3}>
          Enrollment — {employee ? employee.full_name : `Nhân viên #${id}`}
        </Title>
        {employee && (
          <Text c="dimmed" size="sm">
            Mã: {employee.employee_code} · {employee.department} · {employee.position}
          </Text>
        )}
      </Stack>

      {/* Upload form — ẩn sau khi đã submit */}
      {!jobId && (
        <Paper withBorder p="lg" radius="md">
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Upload 1–5 ảnh chân dung rõ nét (JPEG/PNG, tối đa 5MB/ảnh). Ảnh tốt nhất: mặt
              thẳng, đủ ánh sáng, chỉ một người trong khung.
            </Text>

            <Dropzone
              onDrop={(dropped) =>
                setFiles((prev) => [...prev, ...dropped].slice(0, MAX_FILES))
              }
              onReject={() =>
                notifications.show({
                  color: "red",
                  message: "File không hợp lệ. Chỉ nhận JPEG/PNG, tối đa 5MB/ảnh.",
                })
              }
              maxSize={MAX_SIZE_BYTES}
              accept={IMAGE_MIME_TYPE}
              maxFiles={MAX_FILES - files.length}
              disabled={files.length >= MAX_FILES}
            >
              <Stack align="center" gap="xs" py="md" style={{ pointerEvents: "none" }}>
                <Text size="sm" fw={500}>
                  Kéo thả ảnh vào đây, hoặc click để chọn
                </Text>
                <Text size="xs" c="dimmed">
                  {files.length}/{MAX_FILES} ảnh đã chọn · JPEG/PNG · tối đa 5MB/ảnh
                </Text>
              </Stack>
            </Dropzone>

            {/* Danh sách file đã chọn */}
            {files.length > 0 && (
              <Stack gap={4}>
                {files.map((f, i) => (
                  <Group key={i} justify="space-between" wrap="nowrap">
                    <Text size="sm" truncate style={{ flex: 1 }}>
                      {f.name}{" "}
                      <Text span c="dimmed" size="xs">
                        ({(f.size / 1024).toFixed(0)} KB)
                      </Text>
                    </Text>
                    <Button
                      size="xs"
                      variant="subtle"
                      color="red"
                      onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                    >
                      Xoá
                    </Button>
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
              >
                Upload & Enroll ({files.length} ảnh)
              </Button>
            </Group>
          </Stack>
        </Paper>
      )}

      {/* Kết quả polling */}
      {jobId && (
        <Paper withBorder p="lg" radius="md">
          <Stack gap="md">
            <Group justify="space-between">
              <Text fw={500}>Trạng thái xử lý</Text>
              <Badge color={statusColor} variant="light" size="md">
                {statusLabel}
              </Badge>
            </Group>

            {!isDone && <Progress value={100} animated color="blue" />}

            {jobStatus && (
              <Stack gap={6}>
                <Text size="sm">
                  ✅ Ảnh xử lý thành công:{" "}
                  <Text span fw={600}>
                    {jobStatus.processed_count}
                  </Text>
                </Text>
                <Text size="sm">
                  ❌ Ảnh thất bại:{" "}
                  <Text span fw={600}>
                    {jobStatus.failed_count}
                  </Text>
                </Text>
                {jobStatus.message && (
                  <Text size="sm" c="dimmed">
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
                  <Button
                    color="green"
                    onClick={() => navigate("/admin/employees")}
                  >
                    Xong ✓
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
