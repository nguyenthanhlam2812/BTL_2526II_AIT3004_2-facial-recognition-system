import { useEffect } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Group,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useForm, isNotEmpty } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconArrowLeft, IconDeviceFloppy } from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { createEmployee, updateEmployee } from "@/shared/api/employees";
import type { Employee, EmployeeCreate, EmployeeStatus } from "@/shared/types/api";
import PageHeader from "@/shared/ui/PageHeader";

export default function EmployeeFormPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { state } = useLocation();
  const queryClient = useQueryClient();

  const isEdit = !!id;
  const employee = state?.employee as Employee | undefined;

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
    <Stack gap="lg" maw={640}>
      <PageHeader
        title={isEdit ? "Sửa nhân viên" : "Tạo nhân viên"}
        subtitle="Thông tin này dùng để hiển thị ở dashboard, lịch sử chấm công và kết quả kiosk."
        actions={
          <Button
            variant="subtle"
            leftSection={<IconArrowLeft size={17} />}
            onClick={() => navigate("/admin/employees")}
          >
            Quay lại
          </Button>
        }
      />

      <Paper
        withBorder
        p={{ base: "lg", sm: "xl" }}
        style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
      >
        <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
          <Stack gap="md">
            <TextInput
              label="Mã nhân viên"
              description="Nên dùng mã ngắn, duy nhất, dễ đối chiếu khi demo."
              placeholder="E001"
              {...form.getInputProps("employee_code")}
            />
            <TextInput
              label="Họ và tên"
              description="Tên sẽ xuất hiện ở overlay kiosk khi nhận diện thành công."
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

            <Stack gap={6}>
              <Text size="sm" fw={500}>
                Trạng thái
              </Text>
              <SegmentedControl
                value={form.values.status}
                onChange={(value) => form.setFieldValue("status", value as EmployeeStatus)}
                data={[
                  { value: "active", label: "Hoạt động" },
                  { value: "inactive", label: "Tạm ngừng" },
                ]}
              />
              <Text size="xs" c="var(--text-muted)">
                Nhân viên tạm ngừng vẫn giữ lịch sử, nhưng không nên dùng để demo check-in mới.
              </Text>
            </Stack>

            <Group justify="flex-end" mt="xs">
              <Button variant="default" onClick={() => navigate("/admin/employees")}>
                Huỷ
              </Button>
              <Button
                type="submit"
                loading={mutation.isPending}
                leftSection={<IconDeviceFloppy size={17} />}
              >
                {isEdit ? "Cập nhật" : "Tạo"}
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Stack>
  );
}
