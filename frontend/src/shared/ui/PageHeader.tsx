import type { ReactNode } from "react";
import { Group, Stack, Text, Title } from "@mantine/core";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
};

export default function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <Group justify="space-between" align="flex-start" gap="md" wrap="wrap">
      <Stack gap={4} style={{ minWidth: 260, flex: 1 }}>
        <Title order={2} size="h2" c="var(--text-primary)">
          {title}
        </Title>
        {subtitle && (
          <Text size="sm" c="var(--text-secondary)">
            {subtitle}
          </Text>
        )}
      </Stack>
      {actions}
    </Group>
  );
}
