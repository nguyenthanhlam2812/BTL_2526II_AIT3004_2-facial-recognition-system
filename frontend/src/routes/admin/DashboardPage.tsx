import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import "dayjs/locale/vi";
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

type TrendPoint = {
  label: string;
  value: number;
};

type DonutSegment = {
  name: string;
  value: number;
  color: string;
};

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

function timezoneLabel(timezone?: string) {
  if (!timezone) return "...";
  if (timezone === "Asia/Ho_Chi_Minh") return "giờ Việt Nam";
  if (timezone === "Asia/Bangkok") return "giờ Bangkok";
  if (timezone === "UTC") return "giờ UTC";
  return timezone;
}

function eventTimestamp(event: AttendanceEvent) {
  return event.captured_at ?? event.created_at;
}

function TrendChart({ data }: { data: TrendPoint[] }) {
  const width = 640;
  const height = 270;
  const padding = { top: 18, right: 18, bottom: 34, left: 38 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const points = data.length ? data : [{ label: "", value: 0 }];
  const maxValue = Math.max(1, ...points.map((point) => point.value));
  const baselineY = padding.top + innerHeight;
  const xFor = (index: number) =>
    padding.left + (points.length === 1 ? innerWidth / 2 : (index * innerWidth) / (points.length - 1));
  const yFor = (value: number) => baselineY - (value / maxValue) * innerHeight;
  const coordinates = points.map((point, index) => ({
    ...point,
    x: xFor(index),
    y: yFor(point.value),
  }));
  const linePath = coordinates.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  const firstCoordinate = coordinates[0] ?? { x: padding.left, y: baselineY };
  const lastCoordinate = coordinates[coordinates.length - 1] ?? firstCoordinate;
  const areaPath = `${linePath} L ${lastCoordinate.x} ${baselineY} L ${firstCoordinate.x} ${baselineY} Z`;
  const labelEvery = points.length > 10 ? Math.ceil(points.length / 6) : 1;
  const gridLines = Array.from({ length: 5 }, (_, index) => {
    const y = padding.top + (index * innerHeight) / 4;
    const value = Math.round(maxValue - (index * maxValue) / 4);
    return { y, value };
  });

  return (
    <Box style={{ width: "100%", minWidth: 0, height }}>
      <svg
        aria-label="Daily check-in trend"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height="100%"
      >
        <defs>
          <linearGradient id="dashboardTrendFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--accent-primary)" stopOpacity="0.36" />
            <stop offset="100%" stopColor="var(--accent-primary)" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {gridLines.map((line) => (
          <g key={line.y}>
            <line
              x1={padding.left}
              x2={width - padding.right}
              y1={line.y}
              y2={line.y}
              stroke="var(--border-strong)"
              strokeDasharray="5 5"
            />
            <text x={10} y={line.y + 4} fill="var(--text-muted)" fontSize="11">
              {line.value}
            </text>
          </g>
        ))}
        <path d={areaPath} fill="url(#dashboardTrendFill)" />
        <path d={linePath} fill="none" stroke="var(--accent-primary)" strokeWidth="3" />
        {coordinates.map((point, index) => (
          <g key={`${point.label}-${index}`}>
            <circle cx={point.x} cy={point.y} r="4" fill="var(--accent-primary-2)" />
            {(index % labelEvery === 0 || index === coordinates.length - 1) && (
              <text
                x={point.x}
                y={height - 10}
                fill="var(--text-muted)"
                fontSize="11"
                textAnchor="middle"
              >
                {point.label}
              </text>
            )}
          </g>
        ))}
      </svg>
    </Box>
  );
}

function StatusDonut({ data, total }: { data: DonutSegment[]; total: number }) {
  const size = 220;
  const center = size / 2;
  const radius = 76;
  const strokeWidth = 26;
  const circumference = 2 * Math.PI * radius;
  const sum = Math.max(1, data.reduce((acc, item) => acc + item.value, 0));
  const fallbackColors = ["var(--success)", "var(--warning)", "var(--danger)", "var(--border-strong)"];
  const segments = data.map((segment, index) => {
    const previousLength = data
      .slice(0, index)
      .reduce((acc, item) => acc + (item.value / sum) * circumference, 0);
    const length = (segment.value / sum) * circumference;
    return {
      ...segment,
      length,
      dashOffset: -previousLength,
      stroke: segment.color.includes(".") ? (fallbackColors[index] ?? fallbackColors[3]) : segment.color,
    };
  });

  return (
    <Box style={{ width: "100%", minWidth: 0, height: 240, display: "grid", placeItems: "center" }}>
      <svg aria-label="Today attendance status" role="img" viewBox={`0 0 ${size} ${size}`} width={220} height={220}>
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="var(--border-strong)"
          strokeWidth={strokeWidth}
          opacity="0.55"
        />
        {segments.map((segment, index) => (
          <circle
            key={`${segment.name}-${index}`}
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={segment.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={`${segment.length} ${circumference - segment.length}`}
            strokeDashoffset={segment.dashOffset}
            strokeLinecap="round"
            transform={`rotate(-90 ${center} ${center})`}
          />
        ))}
        <text x={center} y={center - 4} textAnchor="middle" fill="var(--text-primary)" fontSize="34" fontWeight="800">
          {total}
        </text>
        <text x={center} y={center + 24} textAnchor="middle" fill="var(--text-muted)" fontSize="12">
          nhân viên
        </text>
      </svg>
    </Box>
  );
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

  const chartData = useMemo<TrendPoint[]>(() => {
    const days = Number(range);
    return (
      summary?.trend.map((point) => ({
        label: dayjs(point.date).format(days > 7 ? "DD/MM" : "ddd"),
        value: point.check_in_count,
      })) ?? []
    );
  }, [range, summary?.trend]);

  const donutData: DonutSegment[] =
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
        subtitle={`${dayjs().format("dddd, DD/MM/YYYY")} · ${timezoneLabel(summary?.business_timezone)}`}
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
          delta="Theo báo cáo"
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
            minWidth: 0,
          }}
        >
          <Stack gap="lg">
            <Group justify="space-between">
              <Stack gap={2}>
                <Text fw={700}>Check-in theo ngày</Text>
                <Text size="sm" c="var(--text-secondary)">
                  Tính theo múi giờ chấm công
                </Text>
              </Stack>
              <IconCalendarStats size={22} color="var(--accent-primary-2)" />
            </Group>
            <TrendChart data={chartData} />
          </Stack>
        </Paper>

        <Paper
          withBorder
          p="lg"
          style={{
            background: "var(--bg-card)",
            borderColor: "var(--border-subtle)",
            minWidth: 0,
          }}
        >
          <Stack gap="lg">
            <Stack gap={2}>
              <Text fw={700}>Trạng thái hôm nay</Text>
              <Text size="sm" c="var(--text-secondary)">
                Tổng hợp từ báo cáo hôm nay
              </Text>
            </Stack>
            <StatusDonut data={donutData} total={totalEmployees} />
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
              Các sự kiện check-in/out gần nhất từ kiosk
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
          Mở kiosk chấm công
        </Button>
      </Group>
    </Stack>
  );
}
