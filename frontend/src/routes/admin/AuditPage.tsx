import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import {
  Badge,
  Button,
  Group,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconRefresh, IconSearch } from "@tabler/icons-react";
import { listAuditLogs } from "@/shared/api/auditLogs";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { isOwner } from "@/shared/lib/access";
import type { AuditLog } from "@/shared/types/api";
import AccessDeniedState from "@/shared/ui/AccessDeniedState";
import PageHeader from "@/shared/ui/PageHeader";

const PAGE_SIZE = 15;

const RESOURCE_TYPE_OPTIONS = [
  { value: "user", label: "Người dùng" },
  { value: "employee", label: "Nhân viên" },
  { value: "enrollment", label: "Enrollment" },
  { value: "attendance_event", label: "Chấm công" },
  { value: "system_setting", label: "Cấu hình" },
  { value: "auth", label: "Tài khoản" },
];

const ACTION_LABELS: Record<string, string> = {
  "admin_user.create": "Tạo user",
  "admin_user.update": "Sửa user",
  "admin_user.reset_password": "Reset mật khẩu",
  "admin_user.delete": "Xóa user",
  "employee.create": "Tạo nhân viên",
  "employee.update": "Sửa nhân viên",
  "employee.delete": "Xóa nhân viên",
  "enrollment.submit": "Gửi enrollment",
  "attendance_event.delete_selected": "Xóa chấm công đã chọn",
  "attendance_event.delete_all": "Xóa toàn bộ chấm công",
  "system_setting.update": "Sửa cấu hình",
  "system_setting.reset": "Reset cấu hình",
  "auth.change_password": "Đổi mật khẩu",
};

function actionColor(action: string) {
  if (action.includes("delete")) return "red";
  if (action.includes("reset")) return "yellow";
  if (action.includes("create") || action.includes("submit")) return "teal";
  if (action.includes("update") || action.includes("change")) return "blue";
  return "gray";
}

function resourceLabel(type: string) {
  return RESOURCE_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (typeof value === "boolean") return value ? "true" : "false";
  if (value === null || value === undefined) return "-";
  return String(value);
}

function metadataSummary(metadata: AuditLog["metadata"]) {
  const keys = [
    "keys",
    "deleted_count",
    "requested_count",
    "event_ids",
    "job_id",
    "employee_id",
    "employee_code",
    "department",
    "status",
    "role",
    "is_active",
    "updated_fields",
    "reset_all",
  ].filter((key) => Object.prototype.hasOwnProperty.call(metadata, key));

  if (!keys.length) return "-";

  return keys
    .slice(0, 4)
    .map((key) => `${key}: ${formatValue(metadata[key])}`)
    .join(" · ");
}

function actorLabel(log: AuditLog) {
  if (!log.actor_username) return "System";
  return log.actor_role ? `${log.actor_username} (${log.actor_role})` : log.actor_username;
}

export default function AuditPage() {
  const { user } = useRequireAuth();
  const canViewAudit = isOwner(user?.role);
  const [search, setSearch] = useState("");
  const [debouncedSearch] = useDebouncedValue(search, 300);
  const [resourceType, setResourceType] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ["audit-logs", { q: debouncedSearch, resourceType, page }],
    queryFn: () =>
      listAuditLogs({
        q: debouncedSearch || undefined,
        resource_type: resourceType || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: canViewAudit,
  });

  if (!canViewAudit) {
    return (
      <AccessDeniedState
        title="Không đủ quyền xem audit log"
        message="Chỉ owner được xem lịch sử thao tác quản trị và cấu hình hệ thống."
        onAction={() => window.history.back()}
      />
    );
  }

  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);
  const rows = data?.items.map((log) => (
    <Table.Tr key={log.id}>
      <Table.Td fz="sm" className="mono" style={{ whiteSpace: "nowrap" }}>
        {dayjs(log.created_at).format("DD/MM/YYYY HH:mm:ss")}
      </Table.Td>
      <Table.Td>
        <Stack gap={2}>
          <Text size="sm" fw={600}>
            {actorLabel(log)}
          </Text>
          {log.actor_user_id && (
            <Text size="xs" c="var(--text-muted)" className="mono">
              #{log.actor_user_id}
            </Text>
          )}
        </Stack>
      </Table.Td>
      <Table.Td>
        <Badge color={actionColor(log.action)} variant="light">
          {ACTION_LABELS[log.action] ?? log.action}
        </Badge>
      </Table.Td>
      <Table.Td>
        <Stack gap={2}>
          <Group gap="xs" wrap="nowrap">
            <Badge color="gray" variant="outline">
              {resourceLabel(log.resource_type)}
            </Badge>
            {log.resource_id && (
              <Text size="xs" c="var(--text-muted)" className="mono">
                #{log.resource_id}
              </Text>
            )}
          </Group>
          <Text size="sm" c="var(--text-secondary)">
            {log.resource_label ?? "-"}
          </Text>
        </Stack>
      </Table.Td>
      <Table.Td c="var(--text-secondary)" fz="sm">
        {metadataSummary(log.metadata)}
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <Stack gap="lg">
      <PageHeader
        title="Nhật ký thao tác"
        subtitle="Theo dõi các thao tác quản trị quan trọng trong hệ thống."
        actions={
          <Button
            variant="default"
            leftSection={<IconRefresh size={18} />}
            loading={isFetching && !isLoading}
            onClick={() => refetch()}
          >
            Làm mới
          </Button>
        }
      />

      <Paper
        withBorder
        p="md"
        style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
      >
        <Group gap="sm" wrap="wrap">
          <TextInput
            placeholder="Tìm người thao tác, hành động, đối tượng..."
            value={search}
            onChange={(event) => {
              setSearch(event.currentTarget.value);
              setPage(1);
            }}
            leftSection={<IconSearch size={17} />}
            maw={380}
          />
          <Select
            placeholder="Tất cả đối tượng"
            data={RESOURCE_TYPE_OPTIONS}
            value={resourceType}
            onChange={(value) => {
              setResourceType(value);
              setPage(1);
            }}
            clearable
            w={220}
          />
        </Group>
      </Paper>

      <Paper className="table-shell" p={0}>
        <Table highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Thời gian</Table.Th>
              <Table.Th>Người thao tác</Table.Th>
              <Table.Th>Hành động</Table.Th>
              <Table.Th>Đối tượng</Table.Th>
              <Table.Th>Chi tiết</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <Table.Tr>
                <Table.Td colSpan={5} ta="center" c="var(--text-secondary)" py="xl">
                  Đang tải...
                </Table.Td>
              </Table.Tr>
            ) : rows?.length ? (
              rows
            ) : (
              <Table.Tr>
                <Table.Td colSpan={5} ta="center" c="var(--text-secondary)" py="xl">
                  Chưa có nhật ký thao tác nào.
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      <Group justify="space-between" align="center">
        {data && (
          <Text size="sm" c="var(--text-secondary)">
            Tổng: {data.total} bản ghi
          </Text>
        )}
        {totalPages > 1 && (
          <Pagination value={page} onChange={setPage} total={totalPages} />
        )}
      </Group>
    </Stack>
  );
}
