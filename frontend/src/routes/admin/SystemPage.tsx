import type { ReactNode } from "react";
import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Box,
  Button,
  Code,
  Group,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Text,
  ThemeIcon,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  IconBrain,
  IconCpu,
  IconDatabase,
  IconDeviceFloppy,
  IconRefresh,
} from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { getSystemSettings, resetSystemSettings, updateSystemSettings } from "@/shared/api/system";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { isOwner } from "@/shared/lib/access";
import type { SystemSettingsUpdate } from "@/shared/types/api";
import AccessDeniedState from "@/shared/ui/AccessDeniedState";
import PageHeader from "@/shared/ui/PageHeader";

function displayNumber(value: number) {
  return Number.isInteger(value) ? String(value) : value.toString();
}

function getErrorDetail(error: unknown): string {
  const detail = (error as AxiosError<{ detail?: string }>).response?.data?.detail;
  return detail ?? "Không kết nối được máy chủ.";
}

function SettingRow({
  label,
  value,
  source,
}: {
  label: string;
  value: string | number | boolean | null;
  source?: "env" | "db";
}) {
  return (
    <Group justify="space-between" align="flex-start" gap="md" wrap="nowrap">
      <Text size="sm" c="var(--text-secondary)">
        {label}
      </Text>
      <Group gap="xs" justify="flex-end" wrap="wrap">
        {source && (
          <Badge size="xs" color={source === "db" ? "teal" : "gray"} variant="light">
            {source}
          </Badge>
        )}
        {typeof value === "boolean" ? (
          <Badge color={value ? "teal" : "gray"} variant="light">
            {value ? "Bật" : "Tắt"}
          </Badge>
        ) : (
          <Code
            fz="sm"
            className="mono"
            style={{ whiteSpace: "normal", wordBreak: "break-word", textAlign: "right" }}
          >
            {value ?? "Không có"}
          </Code>
        )}
      </Group>
    </Group>
  );
}

function SettingsCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <Paper
      withBorder
      p="lg"
      style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
    >
      <Stack gap="md">
        <Group gap="sm">
          <ThemeIcon
            size={40}
            radius={12}
            variant="light"
            color="brand"
            style={{ background: "rgba(124,92,255,0.1)" }}
          >
            {icon}
          </ThemeIcon>
          <Text fw={700}>{title}</Text>
        </Group>
        <Stack gap="sm">{children}</Stack>
      </Stack>
    </Paper>
  );
}

function toNumber(value: number | string) {
  return typeof value === "number" ? value : Number(value);
}

export default function SystemPage() {
  const queryClient = useQueryClient();
  const { user } = useRequireAuth();
  const canWrite = isOwner(user?.role);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["system-settings"],
    queryFn: getSystemSettings,
    enabled: canWrite,
  });

  const settingsForm = useForm<SystemSettingsUpdate>({
    initialValues: {
      attendance_threshold: 0.3,
      face_min_det_score: 0.5,
      face_min_area_ratio: 0.015,
      face_secondary_area_ratio: 0.35,
      business_timezone: "Asia/Ho_Chi_Minh",
      warmup_face_model: false,
    },
  });

  const syncSettingsForm = (values: SystemSettingsUpdate) => {
    settingsForm.setValues(values);
    settingsForm.setInitialValues(values);
    settingsForm.resetDirty(values);
  };

  useEffect(() => {
    if (!data) return;
    syncSettingsForm({
      attendance_threshold: data.attendance_threshold,
      face_min_det_score: data.face_min_det_score,
      face_min_area_ratio: data.face_min_area_ratio,
      face_secondary_area_ratio: data.face_secondary_area_ratio,
      business_timezone: data.business_timezone as SystemSettingsUpdate["business_timezone"],
      warmup_face_model: data.warmup_face_model,
    });
    // settingsForm is stable for this page; data is the only sync trigger needed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const fieldSource = Object.fromEntries(
    (data?.fields ?? []).map((field) => [field.key, field.source]),
  ) as Record<string, "env" | "db">;

  const refreshDerivedQueries = () => {
    queryClient.invalidateQueries({ queryKey: ["system-settings"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    queryClient.invalidateQueries({ queryKey: ["attendance-daily-reports"] });
    queryClient.invalidateQueries({ queryKey: ["attendance-events"] });
  };

  const buildDirtySettingsPayload = (): SystemSettingsUpdate => {
    const payload: SystemSettingsUpdate = {};

    if (settingsForm.isDirty("attendance_threshold")) {
      payload.attendance_threshold = settingsForm.values.attendance_threshold;
    }
    if (settingsForm.isDirty("face_min_det_score")) {
      payload.face_min_det_score = settingsForm.values.face_min_det_score;
    }
    if (settingsForm.isDirty("face_min_area_ratio")) {
      payload.face_min_area_ratio = settingsForm.values.face_min_area_ratio;
    }
    if (settingsForm.isDirty("face_secondary_area_ratio")) {
      payload.face_secondary_area_ratio = settingsForm.values.face_secondary_area_ratio;
    }
    if (settingsForm.isDirty("business_timezone")) {
      payload.business_timezone = settingsForm.values.business_timezone;
    }
    if (settingsForm.isDirty("warmup_face_model")) {
      payload.warmup_face_model = settingsForm.values.warmup_face_model;
    }

    return payload;
  };

  const updateSettingsMutation = useMutation({
    mutationFn: updateSystemSettings,
    onSuccess(response) {
      syncSettingsForm({
        attendance_threshold: response.attendance_threshold,
        face_min_det_score: response.face_min_det_score,
        face_min_area_ratio: response.face_min_area_ratio,
        face_secondary_area_ratio: response.face_secondary_area_ratio,
        business_timezone: response.business_timezone as SystemSettingsUpdate["business_timezone"],
        warmup_face_model: response.warmup_face_model,
      });
      refreshDerivedQueries();
      notifications.show({ color: "teal", message: "Đã lưu cấu hình hệ thống." });
    },
    onError(error: unknown) {
      notifications.show({
        color: "red",
        title: "Lưu cấu hình thất bại",
        message: getErrorDetail(error),
      });
    },
  });

  const resetSettingsMutation = useMutation({
    mutationFn: () => resetSystemSettings({}),
    onSuccess(response) {
      syncSettingsForm({
        attendance_threshold: response.attendance_threshold,
        face_min_det_score: response.face_min_det_score,
        face_min_area_ratio: response.face_min_area_ratio,
        face_secondary_area_ratio: response.face_secondary_area_ratio,
        business_timezone: response.business_timezone as SystemSettingsUpdate["business_timezone"],
        warmup_face_model: response.warmup_face_model,
      });
      refreshDerivedQueries();
      notifications.show({ color: "teal", message: "Đã reset cấu hình hệ thống." });
    },
    onError(error: unknown) {
      notifications.show({
        color: "red",
        title: "Reset cấu hình thất bại",
        message: getErrorDetail(error),
      });
    },
  });

  if (!canWrite) {
    return (
      <AccessDeniedState
        title="Không đủ quyền xem cấu hình hệ thống"
        message="Cấu hình hệ thống chỉ dành cho owner/system admin. Admin vận hành và viewer không được xem hoặc sửa các tham số kỹ thuật."
        onAction={() => window.history.back()}
      />
    );
  }

  if (isLoading) {
    return (
      <Stack gap="md">
        <PageHeader title="Cấu hình hệ thống" subtitle="Đang tải cấu hình runtime..." />
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          <Skeleton h={240} radius="xl" />
          <Skeleton h={240} radius="xl" />
          <Skeleton h={240} radius="xl" />
          <Skeleton h={240} radius="xl" />
        </SimpleGrid>
      </Stack>
    );
  }

  if (isError || !data) {
    return (
      <Stack gap="md">
        <PageHeader title="Cấu hình hệ thống" />
        <Alert color="red" title="Không tải được cấu hình">
          Vui lòng kiểm tra backend và đăng nhập lại.
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="xl">
      <PageHeader
        title="Cấu hình hệ thống"
        subtitle="Runtime settings an toàn cho recognition và reports."
        actions={
          <Badge variant="light" color={canWrite ? "teal" : "gray"} size="lg">
            {canWrite ? "Có thể sửa" : "Chỉ xem"}
          </Badge>
        }
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <SettingsCard title="Nhận diện khuôn mặt" icon={<IconBrain size={21} stroke={1.8} />}>
          <SettingRow
            label="Ngưỡng chấm công"
            value={displayNumber(data.attendance_threshold)}
            source={fieldSource.attendance_threshold}
          />
          <SettingRow
            label="Điểm phát hiện mặt tối thiểu"
            value={displayNumber(data.face_min_det_score)}
            source={fieldSource.face_min_det_score}
          />
          <SettingRow
            label="Tỷ lệ diện tích mặt tối thiểu"
            value={displayNumber(data.face_min_area_ratio)}
            source={fieldSource.face_min_area_ratio}
          />
          <SettingRow
            label="Tỷ lệ mặt phụ"
            value={displayNumber(data.face_secondary_area_ratio)}
            source={fieldSource.face_secondary_area_ratio}
          />
          <SettingRow label="Model" value={data.insightface_model_name} />
        </SettingsCard>

        <SettingsCard title="Runtime" icon={<IconCpu size={21} stroke={1.8} />}>
          <SettingRow label="Environment" value={data.environment} />
          <SettingRow label="API prefix" value={data.api_prefix} />
          <SettingRow
            label="Business timezone"
            value={data.business_timezone}
            source={fieldSource.business_timezone}
          />
          <SettingRow
            label="Warm-up model"
            value={data.warmup_face_model}
            source={fieldSource.warmup_face_model}
          />
        </SettingsCard>

        <SettingsCard title="Hạ tầng dữ liệu" icon={<IconDatabase size={21} stroke={1.8} />}>
          <SettingRow label="Qdrant URL" value={data.qdrant_url} />
          <SettingRow label="Qdrant collection" value={data.qdrant_collection_employee_faces} />
          <SettingRow label="MinIO endpoint" value={data.minio_endpoint} />
          <SettingRow
            label="Redis"
            value={`${data.redis.scheme}://${data.redis.host}:${data.redis.port ?? ""}/${data.redis.database ?? ""}`}
          />
        </SettingsCard>

      </SimpleGrid>

      <Paper
        withBorder
        p="lg"
        style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
      >
        <form
          onSubmit={settingsForm.onSubmit(() => {
            if (!canWrite) return;
            const payload = buildDirtySettingsPayload();
            if (Object.keys(payload).length === 0) {
              notifications.show({ color: "blue", message: "Không có thay đổi để lưu." });
              return;
            }
            updateSettingsMutation.mutate(payload);
          })}
        >
          <Stack gap="md">
            <Group justify="space-between" align="flex-start">
              <Box>
                <Text fw={700}>Cấu hình runtime có thể sửa</Text>
                <Text size="sm" c="var(--text-secondary)">
                  Chỉ owner được sửa. Secrets và endpoint hạ tầng không nằm trong UI này.
                </Text>
              </Box>
              <Badge color={canWrite ? "teal" : "gray"} variant="light">
                {canWrite ? "Owner" : "Chỉ xem"}
              </Badge>
            </Group>

            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <NumberInput
                label="Ngưỡng chấm công"
                min={0.01}
                max={1}
                step={0.01}
                decimalScale={3}
                disabled={!canWrite}
                value={settingsForm.values.attendance_threshold}
                onChange={(value) =>
                  settingsForm.setFieldValue("attendance_threshold", toNumber(value))
                }
              />
              <NumberInput
                label="Điểm phát hiện mặt tối thiểu"
                min={0}
                max={1}
                step={0.01}
                decimalScale={3}
                disabled={!canWrite}
                value={settingsForm.values.face_min_det_score}
                onChange={(value) =>
                  settingsForm.setFieldValue("face_min_det_score", toNumber(value))
                }
              />
              <NumberInput
                label="Tỷ lệ diện tích mặt tối thiểu"
                min={0.001}
                max={0.5}
                step={0.001}
                decimalScale={4}
                disabled={!canWrite}
                value={settingsForm.values.face_min_area_ratio}
                onChange={(value) =>
                  settingsForm.setFieldValue("face_min_area_ratio", toNumber(value))
                }
              />
              <NumberInput
                label="Tỷ lệ mặt phụ"
                min={0.05}
                max={1}
                step={0.01}
                decimalScale={3}
                disabled={!canWrite}
                value={settingsForm.values.face_secondary_area_ratio}
                onChange={(value) =>
                  settingsForm.setFieldValue("face_secondary_area_ratio", toNumber(value))
                }
              />
              <Select
                label="Business timezone"
                data={["UTC", "Asia/Bangkok", "Asia/Ho_Chi_Minh"]}
                disabled={!canWrite}
                allowDeselect={false}
                value={settingsForm.values.business_timezone}
                onChange={(value) =>
                  settingsForm.setFieldValue(
                    "business_timezone",
                    value as SystemSettingsUpdate["business_timezone"],
                  )
                }
              />
              <Switch
                label="Warm-up model khi backend khởi động"
                description="Cần restart backend để áp dụng."
                disabled={!canWrite}
                checked={Boolean(settingsForm.values.warmup_face_model)}
                onChange={(event) =>
                  settingsForm.setFieldValue("warmup_face_model", event.currentTarget.checked)
                }
              />
            </SimpleGrid>

            <Group justify="flex-end">
              <Button
                variant="default"
                leftSection={<IconRefresh size={17} />}
                disabled={!canWrite}
                loading={resetSettingsMutation.isPending}
                onClick={() => resetSettingsMutation.mutate()}
              >
                Reset mặc định
              </Button>
              <Button
                type="submit"
                leftSection={<IconDeviceFloppy size={17} />}
                disabled={!canWrite}
                loading={updateSettingsMutation.isPending}
              >
                Lưu cấu hình
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Stack>
  );
}
