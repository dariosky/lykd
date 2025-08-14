import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";

// Helper to render with providers
function renderWithProviders(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/"]}
        future={{
          v7_relativeSplatPath: true,
          v7_startTransition: true,
        }}
      >
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// Mock fetch
const mockFetch = vi.fn();
(globalThis as any).fetch = mockFetch;

describe("App", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("renders LYKD title", async () => {
    // Not logged in: user null
    mockFetch.mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/user/me")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ user: null }),
        });
      }
      if (url.endsWith("/api/")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ version: "0.1.0", status: "ok" }),
        });
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`));
    });

    renderWithProviders(<App />);

    expect(await screen.findByAltText("LYKD")).toBeInTheDocument();
    expect(screen.getByText("your likes made social")).toBeInTheDocument();
  });

  it("shows loading state initially", () => {
    // getCurrentUser never resolves
    mockFetch.mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/user/me")) {
        return new Promise(() => {}); // pending
      }
      if (url.endsWith("/api/")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ version: "0.1.0", status: "ok" }),
        });
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`));
    });

    renderWithProviders(<App />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("displays API status when backend responds", async () => {
    // Logged in user + backend ok
    mockFetch.mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/user/me")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            user: {
              id: "1",
              name: "Alice",
              email: "a@example.com",
              username: "alice",
              picture: "pic",
              join_date: "2024-01-01",
              is_admin: false,
            },
          }),
        });
      }
      if (url.endsWith("/api/")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ version: "0.1.0", status: "ok" }),
        });
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`));
    });

    renderWithProviders(<App />);

    await waitFor(() => {
      expect(screen.getByText("Backend: ok")).toBeInTheDocument();
      expect(screen.getByText("Version: 0.1.0")).toBeInTheDocument();
    });
  });

  it("indicates reconnecting when backend fails", async () => {
    // Logged in user + backend error
    mockFetch.mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/user/me")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            user: {
              id: "1",
              name: "Alice",
              email: "a@example.com",
              username: "alice",
              picture: "pic",
              join_date: "2024-01-01",
              is_admin: false,
            },
          }),
        });
      }
      if (url.endsWith("/api/")) {
        return Promise.resolve({
          ok: false,
          status: 500,
          statusText: "Server Error",
          json: async () => ({}),
        });
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`));
    });

    renderWithProviders(<App />);

    // Because queries retry on failure, we show the reconnecting indicator
    await waitFor(() => {
      expect(screen.getByText("Connecting to backend...")).toBeInTheDocument();
    });
  });
});
