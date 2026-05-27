import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import {
  ActionIcon,
  Alert,
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
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconChevronRight,
  IconDownload,
  IconRefresh,
} from "@tabler/icons-react";
import {
  exportDailyAttendanceReportsCsv,
  listDailyAttendanceReports,
  listDailyWorkSessions,
} from "@/shared/api/attendance";
import { listAllEmployees, listEmployeeDepartments } from "@/shared/api/employees";
import type {
  AttendanceDailyReportStatus,
  DailyWorkSessions,
  WorkSession,
} from "@/shared/types/api";
import PageHeader from "@/shared/ui/PageHeader";

const PAGE_SIZE = 20;
const MAX_REPORT_DAYS = 31;

const STATUS_OPTIONS = [
  { value: "present", label: "Có mặt" },
  { value: "late", label: "Đi muộn" },
  { value: "missing", label: "Vắng mặt" },
];

function summaryStatusBadge(status: AttendanceDailyReportStatus) {
  const meta =
    status === "late"
      ? { color: "yellow", label: "Đi muộn" }
      : status === "present"
        ? { color: "teal", label: "Có mặt" }
        : { color: "red", label: "Vắng mặt" };

  return (
    <Badge color={meta.color} variant="light" size="sm">
      {meta.label}
    </Badge>
  );
}

function formatWorkMinutes(minutes: number): string {
  if (minutes <= 0) return "-";
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  if (hours === 0) return `${remaining} phút`;
  if (remaining === 0) return `${hours}h`;
  return `${hours}h${String(remaining).padStart(2, "0")}`;
}

function buildSessionsKey(date: string, employeeId: number): string {
  return `${date}::${employeeId}`;
}

function SessionsDetail({ sessions }: { sessions: WorkSession[] }) {
  if (sessions.length === 0) {
    return (
      <Text size="sm" c="var(--text-secondary)" py="xs">
        Không có session nào trong ngày (chưa có check-in được pair).
      </Text>
    );
  }
  return (
    <Stack gap={6} py="xs">
      <Text size="xs" fw={600} c="var(--text-secondary)" tt="uppercase">
        Chi tiết session (pair-matched)
      </Text>
      <Table withTableBorder withColumnBorders verticalSpacing={4} fz="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={40}>#</Table.Th>
            <Table.Th>Check-in</Table.Th>
            <Table.Th>Check-out</Table.Th>
            <Table.Th>Thời lượng</Table.Th>
            <Table.Th>Trạng thái</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sessions.map((session, index) => (
            <Table.Tr key={index}>
              <Table.Td className="mono">{index + 1}</Table.Td>
              <Table.Td className="mono">
                {session.check_in_at
                  ? dayjs(session.check_in_at).format("HH:mm:ss")
                  : "-"}
              </Table.Td>
              <Table.Td className="mono">
                {session.check_out_at
                  ? dayjs(session.check_out_at).format("HH:mm:ss")
                  : "-"}
              </Table.Td>
              <Table.Td className="mono">
                {session.duration_minutes !== null
                  ? formatWorkMinutes(session.duration_minutes)
                  : "-"}
              </Table.Td>
              <Table.Td>
                {session.is_complete ? (
                  <Badge color="teal" variant="light" size="sm">
                    Hoàn tất
                  </Badge>
                ) : (
                  <Badge color="yellow" variant="light" size="sm">
                    Chưa check-out
                  </Badge>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}

function resolveReportDayCount(from: string | null, to: string | null, todayValue: string) {
  let fromDay = dayjs(from ?? to ?? todayValue);
  let toDay = dayjs(to ?? from ?? todayValue);
  if (fromDay.isAfter(toDay)) {
    [fromDay, toDay] = [toDay, fromDay];
  }
  return toDay.startOf("day").diff(fromDay.startOf("day"), "day") + 1;
}

async function getErrorDetail(error: unknown, fallback: string) {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: unknown } }).response;
    const data = response?.data;
    if (typeof data === "object" && data !== null && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
    }
    if (data instanceof Blob) {
      try {
        const text = await data.text();
        const parsed = JSON.parse(text) as { detail?: unknown };
        if (typeof parsed.detail === "string" && parsed.detail.trim()) {
          return parsed.detail;
        }
      } catch {
        // Fall through to fallback below.
      }
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

export default function ReportsPage() {
  const today = dayjs().format("YYYY-MM-DD");
  const [employeeId, setEmployeeId] = useState<string | null>(null);
  const [department, setDepartment] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [from, setFrom] = useState<string | null>(today);
  const [to, setTo] = useState<string | null>(today);
  const [page, setPage] = useState(1);

  const { data: employees, isLoading: isEmployeesLoading } = useQuery({
    queryKey: ["reports-employees-all"],
    queryFn: listAllEmployees,
  });

  const { data: departments, isLoading: isDepartmentsLoading } = useQuery({
    queryKey: ["reports-departments"],
    queryFn: listEmployeeDepartments,
  });

  const rangeDayCount = useMemo(
    () => resolveReportDayCount(from, to, today),
    [from, to, today],
  );
  const rangeError =
    rangeDayCount > MAX_REPORT_DAYS
      ? `Khoảng ngày không được vượt quá ${MAX_REPORT_DAYS} ngày.`
      : null;

  const reportFilters = {
    from: from ? dayjs(from).format("YYYY-MM-DD") : undefined,
    to: to ? dayjs(to).format("YYYY-MM-DD") : undefined,
    employee_id: employeeId ? Number(employeeId) : undefined,
    department: department || undefined,
    status: (status as AttendanceDailyReportStatus) || undefined,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["attendance-daily-reports", { ...reportFilters, page }],
    queryFn: () =>
      listDailyAttendanceReports({
        ...reportFilters,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: rangeError === null,
  });

  // Sessions query mirrors the same filters so the expandable rows show
  // pair-matched sessions for the visible employees/dates.
  const { data: sessionsData } = useQuery({
    queryKey: ["attendance-daily-sessions", { ...reportFilters, page }],
    queryFn: () =>
      listDailyWorkSessions({
        ...reportFilters,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: rangeError === null,
  });

  const sessionsByKey = useMemo(() => {
    const map = new Map<string, DailyWorkSessions>();
    for (const item of sessionsData?.items ?? []) {
      map.set(buildSessionsKey(item.date, item.employee_id), item);
    }
    return map;
  }, [sessionsData]);

  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const toggleExpand = (key: string) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const exportCsvMutation = useMutation({
    mutationFn: async () => {
      if (rangeError) {
        throw new Error(rangeError);
      }
      return exportDailyAttendanceReportsCsv(reportFilters);
    },
    onSuccess({ blob, filename }) {
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      link.click();
      window.URL.revokeObjectURL(downloadUrl);
      notifications.show({ color: "green", message: "Đã xuất CSV báo cáo." });
    },
    onError: async (error) => {
      notifications.show({
        color: "red",
        message: await getErrorDetail(error, "Xuất báo cáo thất bại."),
      });
    },
  });

  const employeeOptions =
    employees?.map((employee) => ({
      value: String(employee.id),
      label: `${employee.full_name} (${employee.employee_code})`,
    })) ?? [];

  const departmentOptions = (departments ?? []).map((value) => ({ value, label: value }));
  const visibleData = rangeError ? undefined : data;
  const totalPages = Math.ceil((visibleData?.total ?? 0) / PAGE_SIZE);

  function handleReset() {
    setEmployeeId(null);
    setDepartment(null);
    setStatus(null);
    setFrom(today);
    setTo(today);
    setPage(1);
  }

  const rows = visibleData?.items.flatMap((row) => {
    const rowKey = buildSessionsKey(row.date, row.employee_id);
    const isExpanded = expandedKeys.has(rowKey);
    const sessionsRow = sessionsByKey.get(rowKey);
    const totalWorkMinutes = sessionsRow?.total_work_minutes ?? 0;

    return [
      <Table.Tr key={rowKey}>
        <Table.Td w={40}>
          <ActionIcon
            variant="subtle"
            size="sm"
            onClick={() => toggleExpand(rowKey)}
            aria-label={isExpanded ? "Đóng chi tiết session" : "Mở chi tiết session"}
          >
            <IconChevronRight
              size={16}
              style={{
                transform: isExpanded ? "rotate(90deg)" : "none",
                transition: "transform 0.15s ease",
              }}
            />
          </ActionIcon>
        </Table.Td>
        <Table.Td className="mono">{dayjs(row.date).format("DD/MM/YYYY")}</Table.Td>
        <Table.Td className="mono" c="var(--text-secondary)">
          {row.employee_code}
        </Table.Td>
        <Table.Td fw={600}>{row.full_name}</Table.Td>
        <Table.Td c="var(--text-secondary)">{row.department}</Table.Td>
        <Table.Td className="mono" c="var(--text-secondary)">
          {row.first_check_in ? dayjs(row.first_check_in).format("HH:mm:ss") : "-"}
        </Table.Td>
        <Table.Td className="mono" c="var(--text-secondary)">
          {row.last_check_out ? dayjs(row.last_check_out).format("HH:mm:ss") : "-"}
        </Table.Td>
        <Table.Td className="mono" c="var(--text-secondary)">
          {formatWorkMinutes(totalWorkMinutes)}
        </Table.Td>
        <Table.Td>{summaryStatusBadge(row.summary_status)}</Table.Td>
      </Table.Tr>,
      ...(isExpanded
        ? [
            <Table.Tr key={`${rowKey}-detail`}>
              <Table.Td
                colSpan={9}
                style={{ background: "var(--bg-card-subtle, rgba(0,0,0,0.02))" }}
              >
                <SessionsDetail sessions={sessionsRow?.sessions ?? []} />
              </Table.Td>
            </Table.Tr>,
          ]
        : []),
    ];
  });

  return (
    <Stack gap="lg">
      <PageHeader
        title="Báo cáo"
        subtitle="Tổng hợp chấm công hằng ngày từ các sự kiện đã ghi nhận."
        actions={
          <Button
            variant="default"
            leftSection={<IconDownload size={18} />}
            loading={exportCsvMutation.isPending}
            onClick={() => exportCsvMutation.mutate()}
          >
            Export CSV
          </Button>
        }
      />

      <Paper
        withBorder
        p="lg"
        style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
      >
        <Group gap="sm" wrap="wrap" align="flex-end">
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
              isEmployeesLoading ? "Đang tải nhân viên..." : "Không có nhân viên"
            }
            w={260}
          />
          <Select
            label="Phòng ban"
            placeholder="Tất cả"
            data={departmentOptions}
            value={department}
            onChange={(value) => {
              setDepartment(value);
              setPage(1);
            }}
            clearable
            searchable
            nothingFoundMessage={
              isDepartmentsLoading ? "Đang tải phòng ban..." : "Không có phòng ban"
            }
            w={220}
          />
          <Select
            label="Trạng thái"
            placeholder="Tất cả"
            data={STATUS_OPTIONS}
            value={status}
            onChange={(value) => {
              setStatus(value);
              setPage(1);
            }}
            clearable
            w={160}
          />
          <Button variant="default" leftSection={<IconRefresh size={16} />} onClick={handleReset}>
            Xóa lọc
          </Button>
        </Group>
      </Paper>

      {rangeError ? (
        <Alert color="red" icon={<IconAlertCircle size={18} />} title="Khoảng ngày không hợp lệ">
          {rangeError}
        </Alert>
      ) : null}

      <Paper className="table-shell" p={0}>
        <Table highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={40} />
              <Table.Th>Ngày</Table.Th>
              <Table.Th>Mã NV</Table.Th>
              <Table.Th>Họ tên</Table.Th>
              <Table.Th>Phòng ban</Table.Th>
              <Table.Th>Check-in đầu</Table.Th>
              <Table.Th>Check-out cuối</Table.Th>
              <Table.Th>Giờ làm</Table.Th>
              <Table.Th>Trạng thái</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rangeError ? (
              <Table.Tr>
                <Table.Td colSpan={9} ta="center" c="var(--text-secondary)" py="xl">
                  Vui lòng điều chỉnh khoảng ngày để xem báo cáo.
                </Table.Td>
              </Table.Tr>
            ) : isLoading ? (
              <Table.Tr>
                <Table.Td colSpan={9} ta="center" c="var(--text-secondary)" py="xl">
                  Đang tải...
                </Table.Td>
              </Table.Tr>
            ) : rows?.length ? (
              rows
            ) : (
              <Table.Tr>
                <Table.Td colSpan={9} ta="center" c="var(--text-secondary)" py="xl">
                  Không có dòng báo cáo.
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      <Group justify="space-between" align="center">
        {visibleData && (
          <Text size="sm" c="var(--text-secondary)">
            Tổng: {visibleData.total} dòng
          </Text>
        )}
        {totalPages > 1 && <Pagination value={page} onChange={setPage} total={totalPages} />}
      </Group>
    </Stack>
  );
}
