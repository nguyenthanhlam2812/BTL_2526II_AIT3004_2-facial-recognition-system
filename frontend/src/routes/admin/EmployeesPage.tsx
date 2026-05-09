import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Stack,
  Group,
  Title,
  Button,
  TextInput,
  Table,
  Badge,
  Pagination,
  Modal,
  Text,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { listEmployees, deleteEmployee } from "@/shared/api/employees";
import type { Employee } from "@/shared/types/api";

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
    queryFn: () =>
      listEmployees({ q: debouncedSearch || undefined, page, page_size: PAGE_SIZE }),
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
      <Table.Td c="dimmed" fz="sm">
        {emp.employee_code}
      </Table.Td>
      <Table.Td fw={500}>{emp.full_name}</Table.Td>
      <Table.Td>{emp.department}</Table.Td>
      <Table.Td>{emp.position}</Table.Td>
      <Table.Td>
        <Badge color={emp.status === "active" ? "green" : "gray"} variant="light" size="sm">
          {emp.status === "active" ? "Hoạt động" : "Tạm ngừng"}
        </Badge>
      </Table.Td>
      <Table.Td>
        <Group gap={4} wrap="nowrap">
          <Button
            size="xs"
            variant="subtle"
            onClick={() =>
              navigate(`/admin/employees/${emp.id}/edit`, { state: { employee: emp } })
            }
          >
            Sửa
          </Button>
          <Button
            size="xs"
            variant="subtle"
            color="teal"
            onClick={() =>
              navigate(`/admin/employees/${emp.id}/enroll`, { state: { employee: emp } })
            }
          >
            Enroll
          </Button>
          <Button
            size="xs"
            variant="subtle"
            color="red"
            onClick={() => setDeleteTarget(emp)}
          >
            Xoá
          </Button>
        </Group>
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <>
      <Stack p="md" gap="md">
        <Group justify="space-between">
          <Title order={3}>Nhân viên</Title>
          <Button onClick={() => navigate("/admin/employees/new")}>+ Tạo nhân viên</Button>
        </Group>

        <TextInput
          placeholder="Tìm theo tên, mã nhân viên..."
          value={search}
          onChange={(e) => {
            setSearch(e.currentTarget.value);
            setPage(1);
          }}
          w={320}
        />

        <Table striped highlightOnHover withTableBorder>
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
                <Table.Td colSpan={6} ta="center" c="dimmed" py="lg">
                  Đang tải...
                </Table.Td>
              </Table.Tr>
            ) : rows?.length ? (
              rows
            ) : (
              <Table.Tr>
                <Table.Td colSpan={6} ta="center" c="dimmed" py="lg">
                  Chưa có nhân viên nào.
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>

        {totalPages > 1 && (
          <Pagination value={page} onChange={setPage} total={totalPages} />
        )}
      </Stack>

      {/* Modal xác nhận xoá */}
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
