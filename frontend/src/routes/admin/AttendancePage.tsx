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
} from "@mantine/core";
import { DatePickerInput } from "@mantine/dates";
import { IconRefresh } from "@tabler/icons-react";
import { listAttendanceEvents } from "@/shared/api/attendance";
import { listEmployees } from "@/shared/api/employees";
import type { AttendanceActionType, AttendanceStatus } from "@/shared/types/api";
import PageHeader from "@/shared/ui/PageHeader";

const PAGE_SIZE = 15;

const ACTION_OPTIONS = [
  { value: "check_in", label: "Check-in" },
  { value: "check_out", label: "Check-out" },
];

function actionBadge(action: AttendanceActionType) {
  return (
    <Badge color={action === "check_in" ? "blue" : "brand"} variant="light" size="sm">
      {action === "check_in" ? "Check-in" : "Check-out"}
    </Badge>
  );
}

function statusBadge(status: AttendanceStatus) {
  const map: Record<AttendanceStatus, { color: string; label: string }> = {
    recorded: { color: "teal", label: "Ghi nhận" },
    unknown_face: { color: "red", label: "Không nhận ra" },
    multiple_faces: { color: "yellow", label: "Nhiều khuôn mặt" },
  };
  const { color, label } = map[status] ?? { color: "gray", label: status };
  return (
    <Badge color={color} variant="light" size="sm">
      {label}
    </Badge>
  );
}

export default function AttendancePage() {
  const [employeeId, setEmployeeId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<string | null>(null);
  const [from, setFrom] = useState<string | null>(null);
  const [to, setTo] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const { data: employeeList, isLoading: isEmployeeListLoading } = useQuery({
    queryKey: ["employees-all"],
    queryFn: () => listEmployees({ page_size: 100 }),
  });

  const employeeOptions =
    employeeList?.items.map((employee) => ({
      value: String(employee.id),
      label: `${employee.full_name} (${employee.employee_code})`,
    })) ?? [];

  const { data, isLoading } = useQuery({
    queryKey: ["attendance-events", { employeeId, actionType, from, to, page }],
    queryFn: () =>
      listAttendanceEvents({
        employee_id: employeeId ? Number(employeeId) : undefined,
        action_type: (actionType as AttendanceActionType) || undefined,
        from: from ? dayjs(from).startOf("day").toISOString() : undefined,
        to: to ? dayjs(to).endOf("day").toISOString() : undefined,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);

  function handleReset() {
    setEmployeeId(null);
    setActionType(null);
    setFrom(null);
    setTo(null);
    setPage(1);
  }

  const rows = data?.items.map((event) => (
    <Table.Tr key={event.id}>
      <Table.Td fz="sm" className="mono" style={{ whiteSpace: "nowrap" }}>
        {dayjs(event.captured_at).format("DD/MM/YYYY HH:mm:ss")}
      </Table.Td>
      <Table.Td fw={600}>{event.employee?.full_name ?? "—"}</Table.Td>
      <Table.Td c="var(--text-secondary)" fz="sm" className="mono">
        {event.employee?.employee_code ?? "—"}
      </Table.Td>
      <Table.Td>{actionBadge(event.action_type)}</Table.Td>
      <Table.Td>{statusBadge(event.attendance_status)}</Table.Td>
      <Table.Td fz="sm" c="var(--text-secondary)" className="mono">
        {event.score !== null ? event.score.toFixed(3) : "—"}
      </Table.Td>
      <Table.Td fz="sm" c="var(--text-secondary)">
        {event.camera_id ?? "—"}
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <Stack gap="lg">
      <PageHeader
        title="Lịch sử chấm công"
        subtitle="Theo dõi check-in, check-out và kết quả nhận diện từ kiosk."
      />

      <Paper
        withBorder
        p="lg"
        style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
      >
        <Group gap="sm" wrap="wrap" align="flex-end">
          <Select
            label="Nhân viên"
            placeholder="Tất cả"
            data={employeeOptions}
            value={employeeId}
            onChange={(value) => {
              setEmployeeId(value);
              setPage(1);
            }}
            clearable
            searchable
            nothingFoundMessage={
              isEmployeeListLoading ? "Đang tải nhân viên..." : "Không có nhân viên"
            }
            w={260}
          />
          <Select
            label="Loại"
            placeholder="Tất cả"
            data={ACTION_OPTIONS}
            value={actionType}
            onChange={(value) => {
              setActionType(value);
              setPage(1);
            }}
            clearable
            w={150}
          />
          <DatePickerInput
            label="Từ ngày"
            placeholder="DD/MM/YYYY"
            value={from}
            onChange={(value) => {
              setFrom(value);
              setPage(1);
            }}
            clearable
            valueFormat="DD/MM/YYYY"
            w={170}
          />
          <DatePickerInput
            label="Đến ngày"
            placeholder="DD/MM/YYYY"
            value={to}
            onChange={(value) => {
              setTo(value);
              setPage(1);
            }}
            clearable
            valueFormat="DD/MM/YYYY"
            minDate={from ?? undefined}
            w={170}
          />
          <Button variant="default" leftSection={<IconRefresh size={16} />} onClick={handleReset}>
            Xoá lọc
          </Button>
        </Group>
      </Paper>

      <Paper className="table-shell" p={0}>
        <Table highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Thời gian</Table.Th>
              <Table.Th>Họ tên</Table.Th>
              <Table.Th>Mã NV</Table.Th>
              <Table.Th>Hành động</Table.Th>
              <Table.Th>Trạng thái</Table.Th>
              <Table.Th>Điểm số</Table.Th>
              <Table.Th>Camera</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <Table.Tr>
                <Table.Td colSpan={7} ta="center" c="var(--text-secondary)" py="xl">
                  Đang tải...
                </Table.Td>
              </Table.Tr>
            ) : rows?.length ? (
              rows
            ) : (
              <Table.Tr>
                <Table.Td colSpan={7} ta="center" c="var(--text-secondary)" py="xl">
                  Không có dữ liệu chấm công.
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
        {totalPages > 1 && <Pagination value={page} onChange={setPage} total={totalPages} />}
      </Group>
    </Stack>
  );
}
