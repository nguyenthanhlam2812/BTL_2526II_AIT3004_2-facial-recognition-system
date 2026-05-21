import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconPencil, IconPlus, IconScan, IconSearch, IconTrash } from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { deleteEmployee, listEmployeeDepartments, listEmployees } from "@/shared/api/employees";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { canOperate } from "@/shared/lib/access";
import type { Employee, EmployeeFaceDataStatus } from "@/shared/types/api";
import GlowDot from "@/shared/ui/GlowDot";
import PageHeader from "@/shared/ui/PageHeader";

const PAGE_SIZE = 10;

function getErrorDetail(error: unknown, fallback: string) {
  return (error as AxiosError<{ detail?: string }>).response?.data?.detail ?? fallback;
}

function faceDataMeta(status: EmployeeFaceDataStatus) {
  switch (status) {
    case "enrolled":
      return { dot: "success" as const, label: "Đã enroll" };
    case "pending":
      return { dot: "warning" as const, label: "Đang xử lý" };
    case "failed":
      return { dot: "danger" as const, label: "Thất bại" };
    default:
      return { dot: "idle" as const, label: "Thiếu dữ liệu" };
  }
}

export default function EmployeesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useRequireAuth();
  const canMutate = canOperate(user?.role);

  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [deleteTarget, setDeleteTarget] = useState<Employee | null>(null);
  const [debouncedSearch] = useDebouncedValue(search, 300);

  const { data, error, isError, isLoading, refetch } = useQuery({
    queryKey: ["employees", { q: debouncedSearch, department, page }],
    queryFn: () =>
      listEmployees({
        q: debouncedSearch || undefined,
        department: department || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const { data: departmentList, isLoading: isDepartmentListLoading } = useQuery({
    queryKey: ["employees", "departments"],
    queryFn: listEmployeeDepartments,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteEmployee(id),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      notifications.show({ color: "green", message: "Đã xóa nhân viên." });
      setDeleteTarget(null);
    },
    onError(error) {
      notifications.show({
        color: "red",
        title: "Không thể xóa nhân viên",
        message: getErrorDetail(error, "Xóa thất bại, vui lòng thử lại."),
      });
    },
  });

  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);
  const departmentOptions = (departmentList ?? []).map((value) => ({ value, label: value }));

  const rows = data?.items.map((emp) => {
    const faceData = faceDataMeta(emp.face_data_status);

    return (
      <Table.Tr key={emp.id}>
        <Table.Td c="var(--text-secondary)" fz="sm" className="mono">
          {emp.employee_code}
        </Table.Td>
        <Table.Td fw={600}>{emp.full_name}</Table.Td>
        <Table.Td c="var(--text-secondary)">{emp.department}</Table.Td>
        <Table.Td c="var(--text-secondary)">{emp.position}</Table.Td>
        <Table.Td>
          <GlowDot
            status={emp.status === "active" ? "success" : "idle"}
            label={emp.status === "active" ? "Hoạt động" : "Tạm ngưng"}
          />
        </Table.Td>
        <Table.Td>
          <GlowDot status={faceData.dot} label={faceData.label} />
        </Table.Td>
        <Table.Td>
          {canMutate ? (
            <Group gap={4} wrap="nowrap">
              <Tooltip label="Sửa">
                <ActionIcon
                  aria-label="Sửa nhân viên"
                  onClick={() =>
                    navigate(`/admin/employees/${emp.id}/edit`, { state: { employee: emp } })
                  }
                >
                  <IconPencil size={17} />
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Enroll khuôn mặt">
                <ActionIcon
                  aria-label="Enroll khuôn mặt"
                  color="blue"
                  onClick={() =>
                    navigate(`/admin/employees/${emp.id}/enroll`, { state: { employee: emp } })
                  }
                >
                  <IconScan size={17} />
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Xóa">
                <ActionIcon
                  aria-label="Xóa nhân viên"
                  color="red"
                  onClick={() => setDeleteTarget(emp)}
                >
                  <IconTrash size={17} />
                </ActionIcon>
              </Tooltip>
            </Group>
          ) : (
            <Text size="sm" c="var(--text-muted)">
              Chỉ xem
            </Text>
          )}
        </Table.Td>
      </Table.Tr>
    );
  });

  return (
    <>
      <Stack gap="lg">
        <PageHeader
          title="Nhân viên"
          subtitle="Quản lý hồ sơ và dữ liệu enrollment khuôn mặt."
          actions={
            canMutate ? (
              <Button
                leftSection={<IconPlus size={18} />}
                onClick={() => navigate("/admin/employees/new")}
                className="glow-purple"
              >
                Tạo nhân viên
              </Button>
            ) : undefined
          }
        />

        <Paper
          withBorder
          p="md"
          style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
        >
          <Group gap="sm" wrap="wrap">
            <TextInput
              placeholder="Tìm theo tên, mã nhân viên..."
              value={search}
              onChange={(event) => {
                setSearch(event.currentTarget.value);
                setPage(1);
              }}
              leftSection={<IconSearch size={17} />}
              maw={360}
            />
            <Select
              placeholder="Tất cả phòng ban"
              data={departmentOptions}
              value={department}
              onChange={(value) => {
                setDepartment(value);
                setPage(1);
              }}
              clearable
              searchable
              nothingFoundMessage={
                isDepartmentListLoading ? "Đang tải phòng ban..." : "Không có phòng ban"
              }
              w={240}
            />
          </Group>
        </Paper>

        <Paper className="table-shell" p={0}>
          <Table highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Mã</Table.Th>
                <Table.Th>Họ tên</Table.Th>
                <Table.Th>Phòng ban</Table.Th>
                <Table.Th>Chức vụ</Table.Th>
                <Table.Th>Trạng thái</Table.Th>
                <Table.Th>Khuôn mặt</Table.Th>
                <Table.Th>Thao tác</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {isLoading ? (
                <Table.Tr>
                  <Table.Td colSpan={7} ta="center" c="var(--text-secondary)" py="xl">
                    Đang tải...
                  </Table.Td>
                </Table.Tr>
              ) : isError ? (
                <Table.Tr>
                  <Table.Td colSpan={7} ta="center" py="xl">
                    <Stack align="center" gap={6}>
                      <Text fw={600}>Không tải được danh sách nhân viên.</Text>
                      <Text size="sm" c="var(--text-secondary)">
                        {getErrorDetail(error, "Kiểm tra backend rồi thử lại.")}
                      </Text>
                      <Button size="xs" variant="default" onClick={() => void refetch()}>
                        Tải lại
                      </Button>
                    </Stack>
                  </Table.Td>
                </Table.Tr>
              ) : rows?.length ? (
                rows
              ) : (
                <Table.Tr>
                  <Table.Td colSpan={7} ta="center" c="var(--text-secondary)" py="xl">
                    Chưa có nhân viên nào.
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Paper>

        {totalPages > 1 && (
          <Group justify="flex-end">
            <Pagination value={page} onChange={setPage} total={totalPages} />
          </Group>
        )}
      </Stack>

      <Modal
        opened={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Xác nhận xóa"
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            Xóa nhân viên{" "}
            <Text span fw={600}>
              {deleteTarget?.full_name}
            </Text>{" "}
            ({deleteTarget?.employee_code})? Hệ thống chỉ cho xóa hồ sơ nhập nhầm chưa có
            enrollment hoặc lịch sử chấm công. Nếu nhân viên đã có dữ liệu, hãy chuyển trạng
            thái sang Tạm ngưng để giữ nguyên báo cáo.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteTarget(null)}>
              Hủy
            </Button>
            <Button
              color="red"
              loading={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              Xóa
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
