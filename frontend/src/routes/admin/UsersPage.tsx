import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  Pagination,
  Paper,
  PasswordInput,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useForm, isNotEmpty } from "@mantine/form";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconKey, IconPencil, IconPlus, IconSearch, IconTrash } from "@tabler/icons-react";
import type { AxiosError } from "axios";
import {
  createAdminUser,
  deleteAdminUser,
  listAdminUsers,
  resetAdminUserPassword,
  updateAdminUser,
} from "@/shared/api/adminUsers";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { isOwner } from "@/shared/lib/access";
import type { AdminUser, AdminUserCreate, UserRole } from "@/shared/types/api";
import AccessDeniedState from "@/shared/ui/AccessDeniedState";
import PageHeader from "@/shared/ui/PageHeader";

const PAGE_SIZE = 10;

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: "owner", label: "Owner" },
  { value: "admin", label: "Admin" },
  { value: "viewer", label: "Viewer" },
];

const ROLE_MATRIX: { role: UserRole; scope: string; canTest: string }[] = [
  {
    role: "owner",
    scope: "Toàn quyền: quản lý người dùng, đổi quyền, reset mật khẩu, sửa cấu hình hệ thống.",
    canTest: "Vào Người dùng và Cấu hình để kiểm tra quyền ghi.",
  },
  {
    role: "admin",
    scope: "Vận hành: tạo/sửa nhân viên, enrollment, xóa lịch sử chấm công, xem báo cáo.",
    canTest: "Đăng nhập admin rồi kiểm tra không thấy Người dùng và không sửa được Cấu hình.",
  },
  {
    role: "viewer",
    scope: "Chỉ xem: tổng quan, nhân viên, chấm công, báo cáo, cấu hình hệ thống.",
    canTest: "Đăng nhập viewer rồi kiểm tra không có nút tạo/xóa/enroll.",
  },
];

function getErrorDetail(error: unknown, fallback: string) {
  const detail = (error as AxiosError<{ detail?: string }>).response?.data?.detail;
  return detail ?? fallback;
}

function roleBadge(role: UserRole) {
  const color = role === "owner" ? "violet" : role === "admin" ? "blue" : "gray";
  return (
    <Badge color={color} variant="light" style={{ minWidth: 72, justifyContent: "center" }}>
      {role}
    </Badge>
  );
}

export default function UsersPage() {
  const queryClient = useQueryClient();
  const { user } = useRequireAuth();
  const canManageUsers = isOwner(user?.role);
  const [search, setSearch] = useState("");
  const [debouncedSearch] = useDebouncedValue(search, 300);
  const [page, setPage] = useState(1);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [resetUser, setResetUser] = useState<AdminUser | null>(null);
  const [deleteUser, setDeleteUser] = useState<AdminUser | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", { q: debouncedSearch, page }],
    queryFn: () =>
      listAdminUsers({
        q: debouncedSearch || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: canManageUsers,
  });

  const createForm = useForm<AdminUserCreate>({
    initialValues: {
      username: "",
      password: "",
      role: "admin",
      is_active: true,
    },
    validate: {
      username: isNotEmpty("Bắt buộc nhập username."),
      password: (value) => (value.length >= 8 ? null : "Mật khẩu phải dài ít nhất 8 ký tự."),
    },
  });

  const editForm = useForm({
    initialValues: {
      username: "",
      role: "admin" as UserRole,
      is_active: true,
    },
    validate: {
      username: isNotEmpty("Bắt buộc nhập username."),
    },
  });

  const resetForm = useForm({
    initialValues: { password: "" },
    validate: {
      password: (value) => (value.length >= 8 ? null : "Mật khẩu phải dài ít nhất 8 ký tự."),
    },
  });

  const invalidateUsers = () => queryClient.invalidateQueries({ queryKey: ["admin-users"] });

  const createMutation = useMutation({
    mutationFn: createAdminUser,
    onSuccess() {
      invalidateUsers();
      setCreateOpen(false);
      createForm.reset();
      notifications.show({ color: "teal", message: "Đã tạo người dùng quản trị." });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, "Tạo người dùng thất bại."),
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (values: { id: number; username: string; role: UserRole; is_active: boolean }) =>
      updateAdminUser(values.id, {
        username: values.username,
        role: values.role,
        is_active: values.is_active,
      }),
    onSuccess() {
      invalidateUsers();
      setEditingUser(null);
      notifications.show({ color: "teal", message: "Đã cập nhật người dùng quản trị." });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, "Cập nhật người dùng thất bại."),
      });
    },
  });

  const resetMutation = useMutation({
    mutationFn: (values: { id: number; password: string }) =>
      resetAdminUserPassword(values.id, { password: values.password }),
    onSuccess() {
      invalidateUsers();
      setResetUser(null);
      resetForm.reset();
      notifications.show({ color: "teal", message: "Đã reset mật khẩu." });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, "Reset mật khẩu thất bại."),
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAdminUser,
    onSuccess() {
      invalidateUsers();
      setDeleteUser(null);
      notifications.show({ color: "teal", message: "Đã xóa người dùng quản trị." });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, "Xóa người dùng thất bại."),
      });
    },
  });

  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);

  if (!canManageUsers) {
    return (
      <AccessDeniedState
        title="Không đủ quyền quản lý người dùng"
        message="Chỉ owner được tạo, sửa quyền, reset mật khẩu hoặc xóa tài khoản quản trị."
        onAction={() => window.history.back()}
      />
    );
  }

  const rows = data?.items.map((user) => (
    <Table.Tr key={user.id}>
      <Table.Td fw={600}>{user.username}</Table.Td>
      <Table.Td>{roleBadge(user.role)}</Table.Td>
      <Table.Td>
        <Badge color={user.is_active ? "teal" : "gray"} variant="light">
          {user.is_active ? "Hoạt động" : "Đã khóa"}
        </Badge>
      </Table.Td>
      <Table.Td c="var(--text-secondary)" className="mono">
        {new Date(user.updated_at).toLocaleString()}
      </Table.Td>
      <Table.Td>
        <Group gap={4} wrap="nowrap">
          <Tooltip label="Sửa người dùng">
            <ActionIcon
              aria-label="Sửa người dùng"
              onClick={() => {
                setEditingUser(user);
                editForm.setValues({
                  username: user.username,
                  role: user.role,
                  is_active: user.is_active,
                });
              }}
            >
              <IconPencil size={17} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Reset mật khẩu">
            <ActionIcon
              aria-label="Reset mật khẩu"
              color="blue"
              onClick={() => {
                setResetUser(user);
                resetForm.reset();
              }}
            >
              <IconKey size={17} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Xóa người dùng">
            <ActionIcon
              aria-label="Xóa người dùng"
              color="red"
              onClick={() => setDeleteUser(user)}
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
          title="Người dùng"
          subtitle="Quản lý tài khoản quản trị và kiểm thử quyền owner/admin/viewer."
          actions={
            <Button
              leftSection={<IconPlus size={18} />}
              onClick={() => setCreateOpen(true)}
              className="glow-purple"
            >
              Tạo người dùng
            </Button>
          }
        />

        <Paper
          withBorder
          p="md"
          style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
        >
          <Stack gap="sm">
            <Text fw={700}>Ma trận quyền để test nhanh</Text>
            <Table verticalSpacing="xs" horizontalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Quyền</Table.Th>
                  <Table.Th>Quyền chính</Table.Th>
                  <Table.Th>Cách kiểm tra</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {ROLE_MATRIX.map((item) => (
                  <Table.Tr key={item.role}>
                    <Table.Td>{roleBadge(item.role)}</Table.Td>
                    <Table.Td c="var(--text-secondary)" fz="sm">
                      {item.scope}
                    </Table.Td>
                    <Table.Td c="var(--text-secondary)" fz="sm">
                      {item.canTest}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Stack>
        </Paper>

        <Paper
          withBorder
          p="md"
          style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
        >
          <TextInput
            placeholder="Tìm tên đăng nhập..."
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
                <Table.Th>Tên đăng nhập</Table.Th>
                <Table.Th>Quyền</Table.Th>
                <Table.Th>Trạng thái</Table.Th>
                <Table.Th>Cập nhật</Table.Th>
                <Table.Th>Thao tác</Table.Th>
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
                    Chưa có người dùng quản trị nào.
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

      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="Tạo người dùng" centered>
        <form onSubmit={createForm.onSubmit((values) => createMutation.mutate(values))}>
          <Stack gap="md">
            <TextInput label="Tên đăng nhập" {...createForm.getInputProps("username")} />
            <PasswordInput label="Mật khẩu" {...createForm.getInputProps("password")} />
            <Select
              label="Quyền"
              data={ROLE_OPTIONS}
              allowDeselect={false}
              {...createForm.getInputProps("role")}
            />
            <Switch
              label="Đang hoạt động"
              {...createForm.getInputProps("is_active", { type: "checkbox" })}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setCreateOpen(false)}>
                Hủy
              </Button>
              <Button type="submit" loading={createMutation.isPending}>
                Tạo
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={!!editingUser}
        onClose={() => setEditingUser(null)}
        title="Sửa người dùng"
        centered
      >
        <form
          onSubmit={editForm.onSubmit((values) => {
            if (!editingUser) return;
            updateMutation.mutate({
              id: editingUser.id,
              username: values.username,
              role: values.role,
              is_active: values.is_active,
            });
          })}
        >
          <Stack gap="md">
            <TextInput label="Tên đăng nhập" {...editForm.getInputProps("username")} />
            <Select
              label="Quyền"
              data={ROLE_OPTIONS}
              allowDeselect={false}
              {...editForm.getInputProps("role")}
            />
            <Switch
              label="Đang hoạt động"
              {...editForm.getInputProps("is_active", { type: "checkbox" })}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setEditingUser(null)}>
                Hủy
              </Button>
              <Button type="submit" loading={updateMutation.isPending}>
                Lưu
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={!!resetUser}
        onClose={() => setResetUser(null)}
        title={`Reset mật khẩu${resetUser ? `: ${resetUser.username}` : ""}`}
        centered
      >
        <form
          onSubmit={resetForm.onSubmit((values) => {
            if (!resetUser) return;
            resetMutation.mutate({ id: resetUser.id, password: values.password });
          })}
        >
          <Stack gap="md">
            <PasswordInput label="Mật khẩu mới" {...resetForm.getInputProps("password")} />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setResetUser(null)}>
                Hủy
              </Button>
              <Button type="submit" loading={resetMutation.isPending}>
                Reset
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={!!deleteUser}
        onClose={() => setDeleteUser(null)}
        title="Xóa người dùng"
        centered
      >
        <Stack gap="md">
          <Text>
            Xóa <strong>{deleteUser?.username}</strong>? Thao tác này không thể hoàn tác.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteUser(null)}>
              Hủy
            </Button>
            <Button
              color="red"
              loading={deleteMutation.isPending}
              onClick={() => deleteUser && deleteMutation.mutate(deleteUser.id)}
            >
              Xóa
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
