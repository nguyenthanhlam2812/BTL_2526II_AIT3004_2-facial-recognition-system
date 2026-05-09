import { useEffect } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Stack, Group, Title, Button, TextInput, Select, Paper } from "@mantine/core";
import { useForm, isNotEmpty } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import type { AxiosError } from "axios";
import { createEmployee, updateEmployee } from "@/shared/api/employees";
import type { Employee, EmployeeCreate } from "@/shared/types/api";

export default function EmployeeFormPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { state } = useLocation();
  const queryClient = useQueryClient();

  const isEdit = !!id;
  const employee = state?.employee as Employee | undefined;

  // Edit nhưng không có state (reload hoặc vào URL trực tiếp) → về danh sách
  useEffect(() => {
    if (isEdit && !employee) {
      notifications.show({
        color: "yellow",
        message: "Không tìm thấy dữ liệu. Vui lòng chọn lại từ danh sách.",
      });
      navigate("/admin/employees", { replace: true });
    }
  }, [isEdit, employee, navigate]);

  const form = useForm<EmployeeCreate>({
    initialValues: {
      employee_code: employee?.employee_code ?? "",
      full_name: employee?.full_name ?? "",
      department: employee?.department ?? "",
      position: employee?.position ?? "",
      status: employee?.status ?? "active",
    },
    validate: {
      employee_code: isNotEmpty("Bắt buộc nhập mã nhân viên"),
      full_name: isNotEmpty("Bắt buộc nhập họ tên"),
      department: isNotEmpty("Bắt buộc nhập phòng ban"),
      position: isNotEmpty("Bắt buộc nhập chức vụ"),
    },
  });

  const mutation = useMutation({
    mutationFn: (values: EmployeeCreate) =>
      isEdit ? updateEmployee(Number(id), values) : createEmployee(values),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      notifications.show({
        color: "green",
        message: isEdit ? "Cập nhật nhân viên thành công." : "Tạo nhân viên thành công.",
      });
      navigate("/admin/employees");
    },
    onError(err: AxiosError<{ detail?: string }>) {
      notifications.show({
        color: "red",
        title: "Thất bại",
        message: err.response?.data?.detail ?? "Có lỗi xảy ra, vui lòng thử lại.",
      });
    },
  });

  return (
    <Stack p="md" gap="md" maw={560}>
      <Title order={3}>{isEdit ? "Sửa nhân viên" : "Tạo nhân viên"}</Title>

      <Paper withBorder p="lg" radius="md">
        <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
          <Stack gap="sm">
            <TextInput
              label="Mã nhân viên"
              placeholder="E001"
              {...form.getInputProps("employee_code")}
            />
            <TextInput
              label="Họ và tên"
              placeholder="Nguyễn Văn A"
              {...form.getInputProps("full_name")}
            />
            <TextInput
              label="Phòng ban"
              placeholder="IT"
              {...form.getInputProps("department")}
            />
            <TextInput
              label="Chức vụ"
              placeholder="Software Engineer"
              {...form.getInputProps("position")}
            />
            <Select
              label="Trạng thái"
              data={[
                { value: "active", label: "Hoạt động" },
                { value: "inactive", label: "Tạm ngừng" },
              ]}
              {...form.getInputProps("status")}
            />
            <Group justify="flex-end" mt="xs">
              <Button variant="default" onClick={() => navigate("/admin/employees")}>
                Huỷ
              </Button>
              <Button type="submit" loading={mutation.isPending}>
                {isEdit ? "Cập nhật" : "Tạo"}
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Stack>
  );
}
