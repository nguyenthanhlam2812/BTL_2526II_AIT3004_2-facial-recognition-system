import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import type { AxiosError } from "axios";
import {
  Badge,
  Button,
  Checkbox,
  Group,
  Modal,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { DatePickerInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { IconDownload, IconRefresh, IconTrash } from "@tabler/icons-react";
import {
  deleteAttendanceEvents,
  deleteSelectedAttendanceEvents,
  exportAttendanceEventsCsv,
  listAttendanceEvents,
} from "@/shared/api/attendance";
import { listAllEmployees } from "@/shared/api/employees";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { canOperate } from "@/shared/lib/access";
import type { AttendanceActionType, AttendanceStatus } from "@/shared/types/api";
import PageHeader from "@/shared/ui/PageHeader";

const PAGE_SIZE = 15;

const ACTION_OPTIONS = [
  { value: "check_in", label: "Check-in" },
  { value: "check_out", label: "Check-out" },
];

function getErrorDetail(error: unknown, fallback: string) {
  return (error as AxiosError<{ detail?: string }>).response?.data?.detail ?? fallback;
}

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
    inactive_employee: { color: "gray", label: "Ngưng hoạt động" },
  };
  const { color, label } = map[status] ?? { color: "gray", label: status };
  return (
    <Badge color={color} variant="light" size="sm">
      {label}
    </Badge>
  );
}

export default function AttendancePage() {
  const queryClient = useQueryClient();
  const { user } = useRequireAuth();
  const canMutate = canOperate(user?.role);

  const [employeeId, setEmployeeId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<string | null>(null);
  const [from, setFrom] = useState<string | null>(null);
  const [to, setTo] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [clearModalOpen, setClearModalOpen] = useState(false);
  const [selectedDeleteModalOpen, setSelectedDeleteModalOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const { data: employeeList, isLoading: isEmployeeListLoading } = useQuery({
    queryKey: ["employees-all"],
    queryFn: listAllEmployees,
  });

  const employeeOptions =
    employeeList?.map((employee) => ({
      value: String(employee.id),
      label: `${employee.full_name} (${employee.employee_code})`,
    })) ?? [];

  const attendanceFilters = {
    employee_id: employeeId ? Number(employeeId) : undefined,
    action_type: (actionType as AttendanceActionType) || undefined,
    from: from ? dayjs(from).startOf("day").toISOString() : undefined,
    to: to ? dayjs(to).endOf("day").toISOString() : undefined,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["attendance-events", { employeeId, actionType, from, to, page }],
    queryFn: () =>
      listAttendanceEvents({
        ...attendanceFilters,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const exportCsvMutation = useMutation({
    mutationFn: () => exportAttendanceEventsCsv(attendanceFilters),
    onSuccess({ blob, filename }) {
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      link.click();
      window.URL.revokeObjectURL(downloadUrl);
      notifications.show({ color: "green", message: "Đã xuất file CSV." });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, "Xuất CSV thất bại, vui lòng thử lại."),
      });
    },
  });

  const deleteAllMutation = useMutation({
    mutationFn: deleteAttendanceEvents,
    onSuccess(response) {
      queryClient.invalidateQueries({ queryKey: ["attendance-events"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-attendance-feed"] });
      setSelectedIds([]);
      setPage(1);
      setClearModalOpen(false);
      notifications.show({
        color: "green",
        message: `Đã xóa ${response.deleted_count} bản ghi lịch sử.`,
      });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, "Xóa lịch sử thất bại, vui lòng thử lại."),
      });
    },
  });

  const deleteSelectedMutation = useMutation({
    mutationFn: deleteSelectedAttendanceEvents,
    onSuccess(response) {
      queryClient.invalidateQueries({ queryKey: ["attendance-events"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-attendance-feed"] });
      const remainingTotal = Math.max((data?.total ?? 0) - response.deleted_count, 0);
      const remainingTotalPages = Math.max(1, Math.ceil(remainingTotal / PAGE_SIZE));
      setSelectedIds([]);
      setPage((currentPage) => Math.min(currentPage, remainingTotalPages));
      setSelectedDeleteModalOpen(false);
      notifications.show({
        color: "green",
        message: `Đã xóa ${response.deleted_count} bản ghi đã chọn.`,
      });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, "Xóa bản ghi đã chọn thất bại."),
      });
    },
  });

  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);
  const currentPageIds = data?.items.map((event) => event.id) ?? [];
  const selectedCount = selectedIds.length;
  const selectedIdSet = new Set(selectedIds);
  const selectedOnCurrentPage = currentPageIds.filter((id) => selectedIdSet.has(id));
  const allCurrentPageSelected =
    currentPageIds.length > 0 && selectedOnCurrentPage.length === currentPageIds.length;
  const someCurrentPageSelected = selectedOnCurrentPage.length > 0 && !allCurrentPageSelected;
  const tableColSpan = canMutate ? 8 : 7;

  function handleReset() {
    setEmployeeId(null);
    setActionType(null);
    setFrom(null);
    setTo(null);
    setSelectedIds([]);
    setPage(1);
  }

  function handlePageChange(nextPage: number) {
    setSelectedIds([]);
    setPage(nextPage);
  }

  function toggleSelected(id: number, checked: boolean) {
    setSelectedIds((current) => {
      if (checked) return Array.from(new Set([...current, id]));
      return current.filter((selectedId) => selectedId !== id);
    });
  }

  function toggleCurrentPage(checked: boolean) {
    setSelectedIds((current) => {
      if (checked) return Array.from(new Set([...current, ...currentPageIds]));
      return current.filter((id) => !currentPageIds.includes(id));
    });
  }

  const rows = data?.items.map((event) => (
    <Table.Tr key={event.id}>
      {canMutate && (
        <Table.Td w={48}>
          <Checkbox
            aria-label={`Chọn bản ghi ${event.id}`}
            checked={selectedIdSet.has(event.id)}
            onChange={(eventChange) => toggleSelected(event.id, eventChange.currentTarget.checked)}
          />
        </Table.Td>
      )}
      <Table.Td fz="sm" className="mono" style={{ whiteSpace: "nowrap" }}>
        {dayjs(event.captured_at ?? event.created_at).format("DD/MM/YYYY HH:mm:ss")}
      </Table.Td>
      <Table.Td fw={600}>{event.employee?.full_name ?? "-"}</Table.Td>
      <Table.Td c="var(--text-secondary)" fz="sm" className="mono">
        {event.employee?.employee_code ?? "-"}
      </Table.Td>
      <Table.Td>{actionBadge(event.action_type)}</Table.Td>
      <Table.Td>{statusBadge(event.attendance_status)}</Table.Td>
      <Table.Td fz="sm" c="var(--text-secondary)" className="mono">
        {event.score !== null ? event.score.toFixed(3) : "-"}
      </Table.Td>
      <Table.Td fz="sm" c="var(--text-secondary)">
        {event.camera_id ?? "-"}
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <>
      <Stack gap="lg">
        <PageHeader
          title="Lịch sử chấm công"
          subtitle="Theo dõi check-in, check-out và kết quả nhận diện từ kiosk."
          actions={
            <Group gap="xs">
              <Button
                variant="default"
                leftSection={<IconDownload size={18} />}
                loading={exportCsvMutation.isPending}
                onClick={() => exportCsvMutation.mutate()}
              >
                Export CSV
              </Button>
              {canMutate && (
                <>
                  <Button
                    color="red"
                    variant="light"
                    leftSection={<IconTrash size={18} />}
                    disabled={selectedCount === 0}
                    onClick={() => setSelectedDeleteModalOpen(true)}
                  >
                    Xóa đã chọn{selectedCount ? ` (${selectedCount})` : ""}
                  </Button>
                  <Button
                    color="red"
                    variant="outline"
                    leftSection={<IconTrash size={18} />}
                    onClick={() => setClearModalOpen(true)}
                  >
                    Xóa toàn bộ
                  </Button>
                </>
              )}
            </Group>
          }
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
                setSelectedIds([]);
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
                setSelectedIds([]);
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
                setSelectedIds([]);
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
                setSelectedIds([]);
                setPage(1);
              }}
              clearable
              valueFormat="DD/MM/YYYY"
              minDate={from ?? undefined}
              w={170}
            />
            <Button variant="default" leftSection={<IconRefresh size={16} />} onClick={handleReset}>
              Xóa lọc
            </Button>
          </Group>
        </Paper>

        <Paper className="table-shell" p={0}>
          <Table highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                {canMutate && (
                  <Table.Th w={48}>
                    <Checkbox
                      aria-label="Chọn tất cả bản ghi trên trang hiện tại"
                      checked={allCurrentPageSelected}
                      indeterminate={someCurrentPageSelected}
                      disabled={currentPageIds.length === 0}
                      onChange={(event) => toggleCurrentPage(event.currentTarget.checked)}
                    />
                  </Table.Th>
                )}
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
                  <Table.Td colSpan={tableColSpan} ta="center" c="var(--text-secondary)" py="xl">
                    Đang tải...
                  </Table.Td>
                </Table.Tr>
              ) : rows?.length ? (
                rows
              ) : (
                <Table.Tr>
                  <Table.Td colSpan={tableColSpan} ta="center" c="var(--text-secondary)" py="xl">
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
              {canMutate && selectedCount ? ` - Đã chọn: ${selectedCount}` : ""}
            </Text>
          )}
          {totalPages > 1 && (
            <Pagination value={page} onChange={handlePageChange} total={totalPages} />
          )}
        </Group>
      </Stack>

      <Modal
        opened={clearModalOpen}
        onClose={() => setClearModalOpen(false)}
        title="Xác nhận xóa lịch sử"
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            Xóa toàn bộ lịch sử chấm công? Nhân viên, ảnh enrollment và dữ liệu nhận diện vẫn
            được giữ lại. Thao tác này không thể hoàn tác.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setClearModalOpen(false)}>
              Hủy
            </Button>
            <Button
              color="red"
              loading={deleteAllMutation.isPending}
              onClick={() => deleteAllMutation.mutate()}
            >
              Xóa toàn bộ
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={selectedDeleteModalOpen}
        onClose={() => setSelectedDeleteModalOpen(false)}
        title="Xác nhận xóa bản ghi"
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            Xóa {selectedCount} bản ghi đã chọn? Nhân viên, ảnh enrollment và dữ liệu nhận diện
            vẫn được giữ lại. Thao tác này không thể hoàn tác.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedDeleteModalOpen(false)}>
              Hủy
            </Button>
            <Button
              color="red"
              loading={deleteSelectedMutation.isPending}
              disabled={selectedCount === 0}
              onClick={() => deleteSelectedMutation.mutate(selectedIds)}
            >
              Xóa đã chọn
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
