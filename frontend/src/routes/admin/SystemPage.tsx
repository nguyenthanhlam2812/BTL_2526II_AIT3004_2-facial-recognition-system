import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Box,
  Code,
  Group,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
} from "@mantine/core";
import { IconBrain, IconCpu, IconDatabase } from "@tabler/icons-react";
import { getSystemSettings } from "@/shared/api/system";
import PageHeader from "@/shared/ui/PageHeader";

function displayNumber(value: number) {
  return Number.isInteger(value) ? String(value) : value.toString();
}

function SettingRow({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | null;
}) {
  return (
    <Group justify="space-between" align="flex-start" gap="md" wrap="nowrap">
      <Text size="sm" c="var(--text-secondary)">
        {label}
      </Text>
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
  );
}

function SettingsCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
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

export default function SystemPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["system-settings"],
    queryFn: getSystemSettings,
  });

  if (isLoading) {
    return (
      <Stack gap="md">
        <PageHeader title="Cấu hình hệ thống" subtitle="Đang tải cấu hình runtime..." />
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          <Skeleton h={200} radius="xl" />
          <Skeleton h={200} radius="xl" />
          <Skeleton h={200} radius="xl" />
        </SimpleGrid>
      </Stack>
    );
  }

  if (isError || !data) {
    return (
      <Stack gap="md">
        <PageHeader title="Cấu hình hệ thống" />
        <Alert color="red" title="Không tải được cấu hình">
          Vui lòng kiểm tra backend và đăng nhập lại bằng tài khoản admin.
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="xl">
      <PageHeader
        title="Cấu hình hệ thống"
        subtitle="Các cấu hình không nhạy cảm dùng trong demo và kiểm tra vận hành."
        actions={
          <Badge variant="light" color="brand" size="lg">
            Read-only
          </Badge>
        }
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <SettingsCard title="Nhận diện khuôn mặt" icon={<IconBrain size={21} stroke={1.8} />}>
          <SettingRow label="Model" value={data.insightface_model_name} />
          <SettingRow label="Attendance threshold" value={displayNumber(data.attendance_threshold)} />
          <SettingRow label="Face min det score" value={displayNumber(data.face_min_det_score)} />
          <SettingRow label="Face min area ratio" value={displayNumber(data.face_min_area_ratio)} />
          <SettingRow
            label="Secondary area ratio"
            value={displayNumber(data.face_secondary_area_ratio)}
          />
          <SettingRow label="Warm-up model" value={data.warmup_face_model} />
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

        <Box>
          <SettingsCard title="Runtime" icon={<IconCpu size={21} stroke={1.8} />}>
            <SettingRow label="Environment" value={data.environment} />
            <SettingRow label="API prefix" value={data.api_prefix} />
          </SettingsCard>
        </Box>
      </SimpleGrid>
    </Stack>
  );
}
