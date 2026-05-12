import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import "dayjs/locale/vi";
import { AreaChart, DonutChart } from "@mantine/charts";
import {
  Anchor,
  Box,
  Button,
  Group,
  Paper,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconCalendarStats,
  IconClockExclamation,
  IconLogin2,
  IconUsers,
} from "@tabler/icons-react";
import {
  getAttendanceDashboardSummary,
  listAttendanceEvents,
} from "@/shared/api/attendance";
import type { AttendanceEvent, AttendanceStatus } from "@/shared/types/api";
import GlowDot, { type GlowDotStatus } from "@/shared/ui/GlowDot";
import PageHeader from "@/shared/ui/PageHeader";
import StatCard from "@/shared/ui/StatCard";

dayjs.locale("vi");

const FEED_EVENT_LIMIT = 100;

function statusMeta(status: AttendanceStatus): { label: string; dot: GlowDotStatus } {
  switch (status) {
    case "recorded":
      return { label: "Ghi nhận", dot: "success" };
    case "multiple_faces":
      return { label: "Nhiều khuôn mặt", dot: "warning" };
    case "unknown_face":
      return { label: "Không nhận ra", dot: "danger" };
    default:
      return { label: status, dot: "idle" };
  }
}

function actionLabel(action: AttendanceEvent["action_type"]) {
  return action === "check_in" ? "Check-in" : "Check-out";
}

function eventTimestamp(event: AttendanceEvent) {
  return event.captured_at ?? event.created_at;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [range, setRange] = useState<"7" | "30">("7");

  const { data: summary } = useQuery({
    queryKey: ["dashboard-summary", range],
    queryFn: () =>
      getAttendanceDashboardSummary({
        days: Number(range) as 7 | 30,
      }),
  });

  const { data: events, isLoading: isEventsLoading } = useQuery({
    queryKey: ["dashboard-attendance-feed"],
    queryFn: () => listAttendanceEvents({ page: 1, page_size: FEED_EVENT_LIMIT }),
  });

  const eventItems = useMemo(() => events?.items ?? [], [events?.items]);
  const totalEmployees = summary?.total_employees ?? 0;
  const stats = summary?.today ?? { present: 0, late: 0, absent: 0 };

  const chartData = useMemo(() => {
    const days = Number(range);
    return (
      summary?.trend.map((point) => ({
        date: dayjs(point.date).format(days > 7 ? "DD/MM" : "ddd"),
        "Check-in": point.check_in_count,
      })) ?? []
    );
  }, [range, summary?.trend]);

  const donutData =
    totalEmployees > 0 || stats.present > 0 || stats.late > 0
      ? [
          { name: "Có mặt", value: stats.present, color: "teal.5" },
          { name: "Đi muộn", value: stats.late, color: "yellow.5" },
          { name: "Vắng mặt", value: stats.absent, color: "red.5" },
        ]
      : [{ name: "Chưa có dữ liệu", value: 1, color: "dark.5" }];

  return (
    <Stack gap="xl">
      <PageHeader
        title="Tổng quan"
        subtitle={`${dayjs().format("dddd, DD/MM/YYYY")} · ${summary?.business_timezone ?? "..."}`}
        actions={
          <SegmentedControl
            value={range}
            onChange={(value) => setRange(value as "7" | "30")}
            data={[
              { value: "7", label: "7 ngày" },
              { value: "30", label: "30 ngày" },
            ]}
          />
        }
      />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
        <StatCard
          label="Tổng nhân viên"
          value={totalEmployees}
          accent="purple"
          icon={<IconUsers size={22} stroke={1.8} />}
        />
        <StatCard
          label="Có mặt hôm nay"
          value={stats.present}
          accent="success"
          delta="Theo report"
          icon={<IconLogin2 size={22} stroke={1.8} />}
        />
        <StatCard
          label="Đi muộn sau 09:00"
          value={stats.late}
          accent="blue"
          icon={<IconClockExclamation size={22} stroke={1.8} />}
        />
        <StatCard
          label="Vắng mặt"
          value={stats.absent}
          accent="danger"
          icon={<IconAlertTriangle size={22} stroke={1.8} />}
        />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="md">
        <Paper
          withBorder
          className="dashboard-chart-main"
          p="lg"
          style={{
            background: "var(--bg-card)",
            borderColor: "var(--border-subtle)",
          }}
        >
          <Stack gap="lg">
            <Group justify="space-between">
              <Stack gap={2}>
                <Text fw={700}>Check-in theo ngày</Text>
                <Text size="sm" c="var(--text-secondary)">
                  Tổng hợp backend theo business timezone
                </Text>
              </Stack>
              <IconCalendarStats size={22} color="var(--accent-primary-2)" />
            </Group>
            <AreaChart
              h={270}
              data={chartData}
              dataKey="date"
              series={[{ name: "Check-in", color: "brand.4" }]}
              curveType="monotone"
              withGradient
              withLegend={false}
              gridAxis="xy"
            />
          </Stack>
        </Paper>

        <Paper
          withBorder
          p="lg"
          style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
        >
          <Stack gap="lg">
            <Stack gap={2}>
              <Text fw={700}>Trạng thái hôm nay</Text>
              <Text size="sm" c="var(--text-secondary)">
                Theo report aggregate của backend
              </Text>
            </Stack>
            <DonutChart h={240} data={donutData} thickness={26} paddingAngle={3} />
            <Stack gap="xs">
              <GlowDot status="success" label={`Có mặt: ${stats.present}`} />
              <GlowDot status="warning" label={`Đi muộn: ${stats.late}`} />
              <GlowDot status="danger" label={`Vắng mặt: ${stats.absent}`} />
            </Stack>
          </Stack>
        </Paper>
      </SimpleGrid>

      <Paper
        withBorder
        p={0}
        style={{
          overflow: "hidden",
          background: "var(--bg-card)",
          borderColor: "var(--border-subtle)",
        }}
      >
        <Group justify="space-between" p="lg" pb="md">
          <Stack gap={2}>
            <Text fw={700}>Hoạt động gần đây</Text>
            <Text size="sm" c="var(--text-secondary)">
              8 sự kiện mới nhất từ kiosk
            </Text>
          </Stack>
          <Anchor size="sm" onClick={() => navigate("/admin/attendance")} style={{ cursor: "pointer" }}>
            Xem tất cả →
          </Anchor>
        </Group>

        <Stack gap={0}>
          {isEventsLoading ? (
            <Text c="var(--text-secondary)" ta="center" py="xl">
              Đang tải dữ liệu...
            </Text>
          ) : eventItems.length ? (
            eventItems.slice(0, 8).map((event) => {
              const meta = statusMeta(event.attendance_status);
              return (
                <Group
                  key={event.id}
                  justify="space-between"
                  px="lg"
                  py="sm"
                  style={{
                    borderTop: "1px solid var(--border-subtle)",
                    minHeight: 58,
                  }}
                >
                  <Group gap="sm" wrap="nowrap">
                    <GlowDot status={meta.dot} />
                    <Box>
                      <Text size="sm" fw={600}>
                        {event.employee?.full_name ?? "Khuôn mặt chưa xác định"}
                      </Text>
                      <Text size="xs" c="var(--text-muted)">
                        {actionLabel(event.action_type)} · {meta.label}
                      </Text>
                    </Box>
                  </Group>
                  <Text size="xs" c="var(--text-muted)" className="mono">
                    {dayjs(eventTimestamp(event)).format("HH:mm:ss")}
                  </Text>
                </Group>
              );
            })
          ) : (
            <Text c="var(--text-secondary)" ta="center" py="xl">
              Chưa có hoạt động nào.
            </Text>
          )}
        </Stack>
      </Paper>

      <Group justify="flex-end">
        <Button variant="subtle" onClick={() => window.open("/kiosk", "_blank")}>
          Mở kiosk
        </Button>
      </Group>
    </Stack>
  );
}
