import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { AppShell, Group, Text, Button, NavLink, Divider } from "@mantine/core";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { clearToken } from "@/shared/lib/token";

export default function AdminLayout() {
  const { user } = useRequireAuth();
  const navigate = useNavigate();
  const location = useLocation();

  function handleLogout() {
    clearToken();
    navigate("/login", { replace: true });
  }

  return (
    <AppShell header={{ height: 56 }} navbar={{ width: 220, breakpoint: "sm" }}>
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Text fw={700} size="lg" c="blue">
            Face Attendance
          </Text>
          <Group gap="xs">
            {user && (
              <Text size="sm" c="dimmed">
                {user.username}
              </Text>
            )}
            <Button variant="subtle" size="xs" color="red" onClick={handleLogout}>
              Logout
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <NavLink
          label="Nhân viên"
          active={location.pathname.startsWith("/admin/employees")}
          onClick={() => navigate("/admin/employees")}
          style={{ borderRadius: 6 }}
        />
        <Divider my={4} />
        <NavLink
          label="Chấm công"
          active={location.pathname.startsWith("/admin/attendance")}
          onClick={() => navigate("/admin/attendance")}
          style={{ borderRadius: 6 }}
        />
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
