import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { createTheme, MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@mantine/dropzone/styles.css";
import "@mantine/dates/styles.css";
import "@mantine/charts/styles.css";
import "./styles/globals.css";

import App from "./App";

const theme = createTheme({
  primaryColor: "brand",
  defaultRadius: "lg",
  fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
  fontFamilyMonospace: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
  headings: {
    fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    fontWeight: "700",
  },
  colors: {
    brand: [
      "#f1edff",
      "#ded6ff",
      "#bdadff",
      "#9b82ff",
      "#7c5cff",
      "#6746f0",
      "#5236c5",
      "#3f2999",
      "#2c1d70",
      "#1d134d",
    ],
    dark: [
      "#e8e8f0",
      "#c8c8d8",
      "#a0a0b8",
      "#77778f",
      "#555568",
      "#373746",
      "#2a2a3a",
      "#1f1f2a",
      "#14141c",
      "#0a0a0f",
    ],
  },
  components: {
    Button: {
      defaultProps: { radius: "md" },
    },
    ActionIcon: {
      defaultProps: { radius: "md", variant: "subtle" },
    },
    Paper: {
      defaultProps: { radius: "xl" },
    },
    TextInput: {
      defaultProps: { radius: "md" },
    },
    PasswordInput: {
      defaultProps: { radius: "md" },
    },
    Select: {
      defaultProps: { radius: "md" },
    },
    Code: {
      defaultProps: { ff: "monospace" },
    },
  },
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider theme={theme} forceColorScheme="dark">
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
);
