import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  AppShell,
  Avatar,
  Box,
  Button,
  Divider,
  Group,
  Menu,
  Modal,
  PasswordInput,
  Stack,
  Text,
  UnstyledButton,
} from "@mantine/core";
import { useForm, isNotEmpty, matchesField } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
  IconActivityHeartbeat,
  IconBuildingCommunity,
  IconCalendarStats,
  IconChevronDown,
  IconClipboardList,
  IconClockHour4,
  IconDashboard,
  IconKey,
  IconLogout,
  IconScan,
  IconSettings,
  IconShieldCheck,
  IconShieldLock,
  IconUserCog,
  IconUsers,
} from "@tabler/icons-react";
import type { AxiosError } from "axios";
import { changePassword } from "@/shared/api/auth";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { clearToken } from "@/shared/lib/token";
import GlowDot from "@/shared/ui/GlowDot";

type NavItem = {
  label: string;
  path: string;
  icon: typeof IconDashboard;
  external?: boolean;
  ownerOnly?: boolean;
};

const navItems: NavItem[] = [
  { label: "Tổng quan", path: "/admin/dashboard", icon: IconDashboard },
  { label: "Nhân viên", path: "/admin/employees", icon: IconUsers },
  { label: "Danh mục", path: "/admin/lookups", icon: IconBuildingCommunity },
  { label: "Chấm công", path: "/admin/attendance", icon: IconClockHour4 },
  { label: "Báo cáo", path: "/admin/reports", icon: IconCalendarStats },
  { label: "Nhật ký", path: "/admin/audit", icon: IconClipboardList, ownerOnly: true },
  { label: "Người dùng", path: "/admin/users", icon: IconUserCog, ownerOnly: true },
  { label: "Cấu hình", path: "/admin/system", icon: IconSettings, ownerOnly: true },
  { label: "Kiosk chấm công", path: "/kiosk", icon: IconScan, external: true },
];

function getErrorDetail(error: unknown): string {
  const detail = (error as AxiosError<{ detail?: string }>).response?.data?.detail;
  return detail ?? "Không kết nối được máy chủ.";
}

function validateNewPassword(value: string) {
  if (!value) return "Nhập mật khẩu mới.";
  if (value !== value.trim()) return "Mật khẩu mới không được bắt đầu hoặc kết thúc bằng khoảng trắng.";
  if (value.length < 8) return "Mật khẩu mới phải dài ít nhất 8 ký tự.";
  if (!/[a-z]/i.test(value) || !/\d/.test(value)) {
    return "Mật khẩu mới cần có ít nhất một chữ cái và một chữ số.";
  }
  return null;
}

export default function AdminLayout() {
  const { user } = useRequireAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);

  const passwordForm = useForm({
    initialValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
    validate: {
      current_password: isNotEmpty("Nhập mật khẩu hiện tại."),
      new_password: validateNewPassword,
      confirm_password: matchesField("new_password", "Mật khẩu xác nhận không khớp."),
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: changePassword,
    onSuccess(response) {
      notifications.show({
        color: "teal",
        title: "Đã cập nhật mật khẩu",
        message: response.message,
      });
      passwordForm.reset();
      setPasswordModalOpen(false);
    },
    onError(error: unknown) {
      notifications.show({
        color: "red",
        title: "Đổi mật khẩu thất bại",
        message: getErrorDetail(error),
      });
    },
  });

  function handleLogout() {
    clearToken();
    navigate("/login", { replace: true });
  }

  return (
    <>
      <AppShell
      header={{ height: 64 }}
      navbar={{ width: 240, breakpoint: "sm" }}
      padding={0}
      styles={{
        header: {
          background: "rgba(16, 16, 24, 0.82)",
          borderColor: "var(--border-subtle)",
          backdropFilter: "blur(18px)",
        },
        navbar: {
          background: "rgba(16, 16, 24, 0.82)",
          borderColor: "var(--border-subtle)",
          backdropFilter: "blur(18px)",
        },
        main: {
          minHeight: "100vh",
        },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="lg" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Box
              style={{
                width: 36,
                height: 36,
                borderRadius: 12,
                display: "grid",
                placeItems: "center",
                background:
                  "linear-gradient(135deg, rgba(124,92,255,0.28), rgba(59,130,246,0.18))",
                boxShadow: "0 0 28px var(--accent-glow)",
                color: "var(--accent-primary)",
              }}
            >
              <IconShieldCheck size={20} stroke={1.8} />
            </Box>
            <Stack gap={0}>
              <Text fw={700} size="md" className="text-glow">
                Face Attendance
              </Text>
              <Text size="xs" c="var(--text-muted)">
                Bảng điều khiển chấm công
              </Text>
            </Stack>
          </Group>

          <Menu position="bottom-end" width={220} shadow="lg">
            <Menu.Target>
              <UnstyledButton
                style={{
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 999,
                  padding: "6px 8px 6px 6px",
                  background: "rgba(255,255,255,0.03)",
                }}
              >
                <Group gap="xs" wrap="nowrap">
                  <Avatar size={30} radius="xl" color="brand">
                    {(user?.username ?? "A").slice(0, 1).toUpperCase()}
                  </Avatar>
                  <Stack gap={0} visibleFrom="xs">
                    <Text size="sm" fw={600}>
                      {user?.username ?? "admin"}
                    </Text>
                    <Text size="xs" c="var(--text-muted)">
                      {user?.role ?? "admin"}
                    </Text>
                  </Stack>
                  <IconChevronDown size={14} color="var(--text-muted)" />
                </Group>
              </UnstyledButton>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Label>Tài khoản đang dùng</Menu.Label>
              <Menu.Item
                leftSection={<IconKey size={16} />}
                onClick={() => setPasswordModalOpen(true)}
              >
                Đổi mật khẩu
              </Menu.Item>
              <Menu.Item leftSection={<IconLogout size={16} />} color="red" onClick={handleLogout}>
                Đăng xuất
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Stack justify="space-between" h="100%" gap="lg">
          <Stack gap={6}>
            {navItems.map((item) => {
              if (item.ownerOnly && user?.role !== "owner") return null;

              const Icon = item.icon;
              const active = item.external
                ? false
                : item.path === "/admin/dashboard"
                  ? location.pathname === "/admin/dashboard" || location.pathname === "/admin"
                  : location.pathname.startsWith(item.path);

              return (
                <UnstyledButton
                  key={item.path}
                  aria-label={item.label}
                  aria-current={active ? "page" : undefined}
                  onClick={() =>
                    item.external ? window.open(item.path, "_blank") : navigate(item.path)
                  }
                  style={{
                    width: "100%",
                    padding: "11px 12px",
                    borderRadius: 14,
                    border: `1px solid ${active ? "rgba(124,92,255,0.28)" : "transparent"}`,
                    borderLeft: `3px solid ${active ? "var(--accent-primary)" : "transparent"}`,
                    background: active ? "rgba(124,92,255,0.11)" : "transparent",
                    boxShadow: active ? "0 12px 30px rgba(124,92,255,0.12)" : "none",
                    color: active ? "var(--text-primary)" : "var(--text-secondary)",
                  }}
                >
                  <Group gap="sm" wrap="nowrap">
                    <Icon
                      size={19}
                      stroke={1.8}
                      color={active ? "var(--accent-primary)" : "var(--text-muted)"}
                    />
                    <Text size="sm" fw={active ? 700 : 500} className={active ? "text-glow" : ""}>
                      {item.label}
                    </Text>
                  </Group>
                </UnstyledButton>
              );
            })}
          </Stack>

          <Stack gap="md">
            <Divider color="var(--border-subtle)" />
            <Box
              p="sm"
              style={{
                border: "1px solid var(--border-subtle)",
                borderRadius: 16,
                background: "rgba(255,255,255,0.025)",
              }}
            >
              <Group justify="space-between" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  <IconActivityHeartbeat size={17} color="var(--accent-primary-2)" />
                  <Text size="xs" c="var(--text-secondary)">
                    Máy chủ
                  </Text>
                </Group>
                <GlowDot status="success" label="Đang hoạt động" />
              </Group>
            </Box>
          </Stack>
        </Stack>
      </AppShell.Navbar>

        <AppShell.Main>
          <Box p={{ base: "md", md: "xl" }}>
            <Outlet />
          </Box>
        </AppShell.Main>
      </AppShell>

      <Modal
        opened={passwordModalOpen}
        onClose={() => {
          setPasswordModalOpen(false);
          passwordForm.reset();
        }}
        title="Đổi mật khẩu"
        centered
      >
        <form
          onSubmit={passwordForm.onSubmit((values) =>
            changePasswordMutation.mutate({
              current_password: values.current_password,
              new_password: values.new_password,
            }),
          )}
        >
          <Stack gap="md">
            <PasswordInput
              label="Mật khẩu hiện tại"
              autoComplete="current-password"
              leftSection={<IconKey size={16} />}
              {...passwordForm.getInputProps("current_password")}
            />
            <PasswordInput
              label="Mật khẩu mới"
              autoComplete="new-password"
              leftSection={<IconShieldLock size={16} />}
              {...passwordForm.getInputProps("new_password")}
            />
            <PasswordInput
              label="Xác nhận mật khẩu mới"
              autoComplete="new-password"
              leftSection={<IconShieldLock size={16} />}
              {...passwordForm.getInputProps("confirm_password")}
            />
            <Group justify="flex-end">
              <Button
                variant="default"
                onClick={() => {
                  setPasswordModalOpen(false);
                  passwordForm.reset();
                }}
              >
                Hủy
              </Button>
              <Button type="submit" loading={changePasswordMutation.isPending}>
                Lưu mật khẩu
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </>
  );
}
