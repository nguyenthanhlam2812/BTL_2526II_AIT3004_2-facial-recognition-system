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
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconPencil, IconPlus, IconScan, IconSearch, IconTrash } from "@tabler/icons-react";
import { deleteEmployee, listEmployees } from "@/shared/api/employees";
import type { Employee } from "@/shared/types/api";
import GlowDot from "@/shared/ui/GlowDot";
import PageHeader from "@/shared/ui/PageHeader";

const PAGE_SIZE = 10;

export default function EmployeesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [deleteTarget, setDeleteTarget] = useState<Employee | null>(null);
  const [debouncedSearch] = useDebouncedValue(search, 300);

  const { data, isLoading } = useQuery({
    queryKey: ["employees", { q: debouncedSearch, page }],
    queryFn: () => listEmployees({ q: debouncedSearch || undefined, page, page_size: PAGE_SIZE }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteEmployee(id),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      notifications.show({ color: "green", message: "Đã xoá nhân viên." });
      setDeleteTarget(null);
    },
    onError() {
      notifications.show({ color: "red", message: "Xoá thất bại, vui lòng thử lại." });
    },
  });

  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);

  const rows = data?.items.map((emp) => (
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
          label={emp.status === "active" ? "Hoạt động" : "Tạm ngừng"}
        />
      </Table.Td>
      <Table.Td>
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
          <Tooltip label="Xoá">
            <ActionIcon
              aria-label="Xoá nhân viên"
              color="red"
              onClick={() => setDeleteTarget(emp)}
            >
              <IconTrash size={17} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <>
      <Stack gap="lg">
        <PageHeader
          title="Nhân viên"
          subtitle="Quản lý hồ sơ và dữ liệu enrollment khuôn mặt."
          actions={
            <Button
              leftSection={<IconPlus size={18} />}
              onClick={() => navigate("/admin/employees/new")}
              className="glow-purple"
            >
              Tạo nhân viên
            </Button>
          }
        />

        <Paper
          withBorder
          p="md"
          style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
        >
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
                <Table.Th>Thao tác</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {isLoading ? (
                <Table.Tr>
                  <Table.Td colSpan={6} ta="center" c="var(--text-secondary)" py="xl">
                    Đang tải...
                  </Table.Td>
                </Table.Tr>
              ) : rows?.length ? (
                rows
              ) : (
                <Table.Tr>
                  <Table.Td colSpan={6} ta="center" c="var(--text-secondary)" py="xl">
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
        title="Xác nhận xoá"
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            Xoá nhân viên{" "}
            <Text span fw={600}>
              {deleteTarget?.full_name}
            </Text>{" "}
            ({deleteTarget?.employee_code})? Thao tác này không thể hoàn tác.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteTarget(null)}>
              Huỷ
            </Button>
            <Button
              color="red"
              loading={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              Xoá
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
