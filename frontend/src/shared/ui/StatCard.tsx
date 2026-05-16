import type { ReactNode } from "react";
import { Box, Group, Paper, Stack, Text } from "@mantine/core";

type StatCardAccent = "purple" | "blue" | "success" | "danger";

type StatCardProps = {
  label: string;
  value: string | number;
  icon: ReactNode;
  delta?: string;
  accent: StatCardAccent;
};

const accentMap: Record<StatCardAccent, { color: string; glow: string }> = {
  purple: { color: "var(--accent-primary)", glow: "rgba(124, 92, 255, 0.14)" },
  blue: { color: "var(--accent-primary-2)", glow: "rgba(59, 130, 246, 0.14)" },
  success: { color: "var(--success)", glow: "rgba(34, 211, 166, 0.12)" },
  danger: { color: "var(--danger)", glow: "rgba(255, 85, 119, 0.12)" },
};

export default function StatCard({ label, value, icon, delta, accent }: StatCardProps) {
  const colors = accentMap[accent];

  return (
    <Paper
      withBorder
      p="lg"
      style={{
        background: "linear-gradient(135deg, var(--bg-card), rgba(26, 26, 36, 0.84))",
        borderColor: "var(--border-subtle)",
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.03), 0 24px 70px ${colors.glow}`,
      }}
    >
      <Stack gap="md">
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Text size="sm" c="var(--text-secondary)">
            {label}
          </Text>
          <Box
            style={{
              width: 42,
              height: 42,
              borderRadius: 12,
              display: "grid",
              placeItems: "center",
              background: colors.glow,
              color: colors.color,
            }}
          >
            {icon}
          </Box>
        </Group>
        <Group justify="space-between" align="flex-end">
          <Text size="32px" fw={700} lh={1} className="mono" c="var(--text-primary)">
            {value}
          </Text>
          {delta && (
            <Text size="xs" c={colors.color} fw={600}>
              {delta}
            </Text>
          )}
        </Group>
      </Stack>
    </Paper>
  );
}
