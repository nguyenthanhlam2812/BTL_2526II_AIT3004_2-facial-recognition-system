import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  IconBuildingCommunity,
  IconBriefcase,
  IconPencil,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";
import type { AxiosError } from "axios";
import {
  createDepartment,
  createPosition,
  deleteDepartment,
  deletePosition,
  listDepartments,
  listPositions,
  updateDepartment,
  updatePosition,
} from "@/shared/api/lookups";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { canOperate } from "@/shared/lib/access";
import type { LookupItem } from "@/shared/types/api";
import PageHeader from "@/shared/ui/PageHeader";

function getErrorDetail(error: unknown, fallback: string) {
  const detail = (error as AxiosError<{ detail?: string }>).response?.data?.detail;
  return detail ?? fallback;
}

function validateName(value: string) {
  const normalized = value.trim();
  if (normalized.length < 2) return "Tên phải dài ít nhất 2 ký tự.";
  if (normalized.length > 64) return "Tên tối đa 64 ký tự.";
  return null;
}

/**
 * A reusable CRUD card for a single lookup type (Department or Position).
 */
function LookupCard({
  title,
  icon,
  queryKey,
  listFn,
  createFn,
  updateFn,
  deleteFn,
  entityLabel,
  canMutate,
}: {
  title: string;
  icon: React.ReactNode;
  queryKey: string;
  listFn: (params?: { q?: string }) => Promise<{ items: LookupItem[]; total: number }>;
  createFn: (name: string) => Promise<LookupItem>;
  updateFn: (id: number, name: string) => Promise<LookupItem>;
  deleteFn: (id: number) => Promise<{ ok: boolean }>;
  entityLabel: string;
  canMutate: boolean;
}) {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editItem, setEditItem] = useState<LookupItem | null>(null);
  const [deleteItem, setDeleteItem] = useState<LookupItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: [queryKey],
    queryFn: () => listFn(),
  });

  const createForm = useForm({
    initialValues: { name: "" },
    validate: { name: validateName },
  });

  const editForm = useForm({
    initialValues: { name: "" },
    validate: { name: validateName },
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: [queryKey] });
    // Also invalidate names queries used in employee form
    queryClient.invalidateQueries({ queryKey: [`${queryKey}-names`] });
    // Invalidate old employees/departments query for backward compat
    queryClient.invalidateQueries({ queryKey: ["employees", "departments"] });
  };

  const createMutation = useMutation({
    mutationFn: (name: string) => createFn(name),
    onSuccess() {
      invalidate();
      setCreateOpen(false);
      createForm.reset();
      notifications.show({ color: "teal", message: `Đã tạo ${entityLabel}.` });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, `Tạo ${entityLabel} thất bại.`),
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => updateFn(id, name),
    onSuccess() {
      invalidate();
      setEditItem(null);
      notifications.show({ color: "teal", message: `Đã cập nhật ${entityLabel}.` });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, `Cập nhật ${entityLabel} thất bại.`),
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteFn(id),
    onSuccess() {
      invalidate();
      setDeleteItem(null);
      notifications.show({ color: "teal", message: `Đã xóa ${entityLabel}.` });
    },
    onError(error) {
      notifications.show({
        color: "red",
        message: getErrorDetail(error, `Xóa ${entityLabel} thất bại.`),
      });
    },
  });

  return (
    <>
      <Paper
        withBorder
        p="lg"
        style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
      >
        <Stack gap="md">
          <Group justify="space-between">
            <Group gap="sm">
              {icon}
              <Text fw={700}>{title}</Text>
              {data && (
                <Text size="sm" c="var(--text-muted)">
                  ({data.total})
                </Text>
              )}
            </Group>
            {canMutate && (
              <Button
                size="xs"
                leftSection={<IconPlus size={14} />}
                onClick={() => setCreateOpen(true)}
              >
                Thêm
              </Button>
            )}
          </Group>

          <Table verticalSpacing="xs" horizontalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Tên</Table.Th>
                {canMutate && <Table.Th w={100}>Thao tác</Table.Th>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {isLoading ? (
                <Table.Tr>
                  <Table.Td colSpan={canMutate ? 2 : 1} ta="center" c="var(--text-secondary)" py="lg">
                    Đang tải...
                  </Table.Td>
                </Table.Tr>
              ) : data?.items.length ? (
                data.items.map((item) => (
                  <Table.Tr key={item.id}>
                    <Table.Td fw={500}>{item.name}</Table.Td>
                    {canMutate && (
                      <Table.Td>
                        <Group gap={4} wrap="nowrap">
                          <Tooltip label="Sửa">
                            <ActionIcon
                              aria-label={`Sửa ${item.name}`}
                              size="sm"
                              onClick={() => {
                                setEditItem(item);
                                editForm.setValues({ name: item.name });
                              }}
                            >
                              <IconPencil size={15} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Xóa">
                            <ActionIcon
                              aria-label={`Xóa ${item.name}`}
                              size="sm"
                              color="red"
                              onClick={() => setDeleteItem(item)}
                            >
                              <IconTrash size={15} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                      </Table.Td>
                    )}
                  </Table.Tr>
                ))
              ) : (
                <Table.Tr>
                  <Table.Td colSpan={canMutate ? 2 : 1} ta="center" c="var(--text-secondary)" py="lg">
                    Chưa có {entityLabel} nào.
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Stack>
      </Paper>

      {/* Create modal */}
      <Modal
        opened={createOpen}
        onClose={() => setCreateOpen(false)}
        title={`Thêm ${entityLabel}`}
        centered
        size="sm"
      >
        <form onSubmit={createForm.onSubmit((values) => createMutation.mutate(values.name.trim()))}>
          <Stack gap="md">
            <TextInput
              label={`Tên ${entityLabel}`}
              placeholder={`Nhập tên ${entityLabel}...`}
              {...createForm.getInputProps("name")}
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

      {/* Edit modal */}
      <Modal
        opened={!!editItem}
        onClose={() => setEditItem(null)}
        title={`Sửa ${entityLabel}`}
        centered
        size="sm"
      >
        <form
          onSubmit={editForm.onSubmit((values) => {
            if (!editItem) return;
            updateMutation.mutate({ id: editItem.id, name: values.name.trim() });
          })}
        >
          <Stack gap="md">
            <TextInput
              label={`Tên ${entityLabel}`}
              {...editForm.getInputProps("name")}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setEditItem(null)}>
                Hủy
              </Button>
              <Button type="submit" loading={updateMutation.isPending}>
                Lưu
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Delete modal */}
      <Modal
        opened={!!deleteItem}
        onClose={() => setDeleteItem(null)}
        title={`Xóa ${entityLabel}`}
        centered
        size="sm"
      >
        <Stack gap="md">
          <Text size="sm">
            Xóa <strong>{deleteItem?.name}</strong>? Nếu còn nhân viên đang dùng giá trị này, thao tác sẽ bị
            từ chối.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteItem(null)}>
              Hủy
            </Button>
            <Button
              color="red"
              loading={deleteMutation.isPending}
              onClick={() => deleteItem && deleteMutation.mutate(deleteItem.id)}
            >
              Xóa
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

export default function LookupsPage() {
  const { user } = useRequireAuth();
  const canMutate = canOperate(user?.role);

  if (!canMutate && user?.role === "viewer") {
    // Viewers can still see the page but can't mutate
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title="Phòng ban & Chức vụ"
        subtitle="Quản lý danh mục phòng ban và chức vụ dùng khi tạo nhân viên."
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <LookupCard
          title="Phòng ban"
          icon={<IconBuildingCommunity size={20} color="var(--accent-primary-2)" />}
          queryKey="lookup-departments"
          listFn={listDepartments}
          createFn={createDepartment}
          updateFn={updateDepartment}
          deleteFn={deleteDepartment}
          entityLabel="phòng ban"
          canMutate={canMutate}
        />
        <LookupCard
          title="Chức vụ"
          icon={<IconBriefcase size={20} color="var(--accent-primary-2)" />}
          queryKey="lookup-positions"
          listFn={listPositions}
          createFn={createPosition}
          updateFn={updatePosition}
          deleteFn={deletePosition}
          entityLabel="chức vụ"
          canMutate={canMutate}
        />
      </SimpleGrid>
    </Stack>
  );
}
