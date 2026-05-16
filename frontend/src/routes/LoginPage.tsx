import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  Box,
  Button,
  Container,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { useForm, isNotEmpty } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconLogin2, IconShieldCheck } from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { login } from "@/shared/api/auth";
import { useAuth } from "@/shared/hooks/useAuth";
import { getToken } from "@/shared/lib/token";

export default function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();

  useEffect(() => {
    if (getToken()) {
      navigate("/admin/dashboard", { replace: true });
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
      navigate("/admin/dashboard", { replace: true });
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
    <Box
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "32px 16px",
        background:
          "radial-gradient(circle at 28% 18%, rgba(124,92,255,0.26), transparent 28rem), radial-gradient(circle at 78% 82%, rgba(59,130,246,0.18), transparent 26rem), var(--bg-base)",
      }}
    >
      <Container size={430} w="100%">
        <Stack gap="lg" align="center">
          <ThemeIcon
            size={58}
            radius={18}
            variant="light"
            color="brand"
            className="glow-purple"
          >
            <IconShieldCheck size={30} stroke={1.8} />
          </ThemeIcon>

          <Paper className="glass" p={{ base: "lg", sm: "xl" }} w="100%">
            <Stack gap="xl">
              <Stack gap={6} ta="center">
                <Title order={1} size="h2">
                  Đăng nhập quản trị
                </Title>
                <Text c="var(--text-secondary)" size="sm">
                  AI Facial Recognition Attendance
                </Text>
              </Stack>

              <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
                <Stack gap="md">
                  <TextInput
                    label="Tên đăng nhập"
                    placeholder="admin"
                    autoComplete="username"
                    size="md"
                    {...form.getInputProps("username")}
                  />
                  <PasswordInput
                    label="Mật khẩu"
                    placeholder="••••••••"
                    autoComplete="current-password"
                    size="md"
                    {...form.getInputProps("password")}
                  />
                  <Button
                    type="submit"
                    fullWidth
                    size="md"
                    mt="xs"
                    loading={mutation.isPending}
                    leftSection={<IconLogin2 size={18} />}
                    className="glow-purple"
                  >
                    Đăng nhập
                  </Button>
                </Stack>
              </form>

              {import.meta.env.DEV && (
                <Text size="xs" c="var(--text-muted)" ta="center" className="mono">
                  Demo: admin / admin123
                </Text>
              )}
            </Stack>
          </Paper>
        </Stack>
      </Container>
    </Box>
  );
}
