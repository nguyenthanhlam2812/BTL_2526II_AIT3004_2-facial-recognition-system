import { Button, Paper, Stack, Text } from "@mantine/core";

type AccessDeniedStateProps = {
  title: string;
  message: string;
  actionLabel?: string;
  onAction: () => void;
};

export default function AccessDeniedState({
  title,
  message,
  actionLabel = "Quay lại",
  onAction,
}: AccessDeniedStateProps) {
  return (
    <Paper
      withBorder
      p="xl"
      maw={640}
      style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
    >
      <Stack gap="md">
        <Stack gap={4}>
          <Text fw={700}>{title}</Text>
          <Text size="sm" c="var(--text-secondary)">
            {message}
          </Text>
        </Stack>
        <Button variant="default" onClick={onAction} w="fit-content">
          {actionLabel}
        </Button>
      </Stack>
    </Paper>
  );
}
