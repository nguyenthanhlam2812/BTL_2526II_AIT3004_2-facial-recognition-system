import { Group, Text } from "@mantine/core";

export type GlowDotStatus = "success" | "warning" | "danger" | "idle";

type GlowDotProps = {
  status: GlowDotStatus;
  label?: string;
};

export default function GlowDot({ status, label }: GlowDotProps) {
  const className = status === "idle" ? "glow-dot" : `glow-dot ${status}`;

  if (!label) {
    return <span className={className} aria-label={status} />;
  }

  return (
    <Group gap={8} wrap="nowrap">
      <span className={className} aria-hidden="true" />
      <Text size="sm" c="var(--text-primary)">
        {label}
      </Text>
    </Group>
  );
}
