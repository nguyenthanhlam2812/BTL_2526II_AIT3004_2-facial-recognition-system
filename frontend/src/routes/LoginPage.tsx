import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  Container,
  Paper,
  Stack,
  Title,
  Text,
  TextInput,
  PasswordInput,
  Button,
} from "@mantine/core";
import { useForm, isNotEmpty } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import type { AxiosError } from "axios";
import { login } from "@/shared/api/auth";
import { useAuth } from "@/shared/hooks/useAuth";
import { getToken } from "@/shared/lib/token";

export default function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();

  // Nếu đã có token: redirect ngay, không hiển thị form
  useEffect(() => {
    if (getToken()) {
      navigate("/admin/employees", { replace: true });
    }
  }, [navigate]);

  const form = useForm({
    initialValues: { username: "", password: "" },
    validate: {
      username: isNotEmpty("Vui lòng nhập tên đăng nhập"),
      password: isNotEmpty("Vui lòng nhập mật khẩu"),
    },
  });

  const mutation = useMutation({
    mutationFn: login,
    onSuccess(data) {
      signIn(data.access_token, data.user);
      navigate("/admin/employees", { replace: true });
    },
    onError(err: AxiosError<{ detail?: string }>) {
      notifications.show({
        color: "red",
        title: "Đăng nhập thất bại",
        message: err.response?.data?.detail ?? "Không kết nối được máy chủ",
      });
    },
  });

  return (
    <Container size="xs" pt={80}>
      <Paper withBorder shadow="sm" p="xl" radius="md">
        <Stack gap="md">
          <Stack gap={4}>
            <Title order={2} ta="center">
              Đăng nhập quản trị
            </Title>
            <Text c="dimmed" size="sm" ta="center">
              AI Facial Recognition Attendance
            </Text>
          </Stack>

          <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
            <Stack gap="sm">
              <TextInput
                label="Tên đăng nhập"
                placeholder="admin"
                autoComplete="username"
                {...form.getInputProps("username")}
              />
              <PasswordInput
                label="Mật khẩu"
                placeholder="••••••••"
                autoComplete="current-password"
                {...form.getInputProps("password")}
              />
              <Button type="submit" fullWidth mt="xs" loading={mutation.isPending}>
                Đăng nhập
              </Button>
            </Stack>
          </form>

          {import.meta.env.DEV && (
            <Text size="xs" c="dimmed" ta="center">
              Demo: admin / admin123
            </Text>
          )}
        </Stack>
      </Paper>
    </Container>
  );
}
