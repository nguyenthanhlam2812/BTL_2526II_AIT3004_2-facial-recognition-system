import { Component, type ErrorInfo, type ReactNode } from "react";
import { Alert, Button, Stack } from "@mantine/core";

type Props = {
  children: ReactNode;
  fallbackTitle?: string;
};

type State = {
  error: Error | null;
};

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ErrorBoundary caught:", error, info);
  }

  handleReset = (): void => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <Stack p="lg" maw={640} mx="auto" my="xl" gap="md">
          <Alert color="red" title={this.props.fallbackTitle ?? "Đã xảy ra lỗi"}>
            {this.state.error.message || "Một thành phần đã gặp sự cố. Vui lòng thử lại."}
          </Alert>
          <Button variant="light" onClick={this.handleReset}>
            Thử lại
          </Button>
        </Stack>
      );
    }
    return this.props.children;
  }
}
