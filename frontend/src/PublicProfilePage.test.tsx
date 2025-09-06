import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import PublicProfilePage from "./PublicProfilePage";

// Helper to render with providers
function renderWithProviders(ui: React.ReactNode, initialEntries: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={initialEntries}
        future={{
          v7_relativeSplatPath: true,
          v7_startTransition: true,
        }}
      >
        <Routes>
          <Route path="/user/:username" element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// Mock fetch
const mockFetch = vi.fn();

describe("PublicProfilePage", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    // Provide fetch mock via Vitest helper (avoids unsafe casts triggering lint errors)
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("shows friendly not found state on 404 without retry", async () => {
    // First call: getCurrentUser (Layout) -> not logged in
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ user: null }),
    });

    // Second call: getPublicProfile -> 404
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({}),
    });

    renderWithProviders(<PublicProfilePage />, ["/user/does-not-exist"]);

    // Wait for the friendly message
    await waitFor(() => {
      expect(screen.getByText("Profile not found")).toBeInTheDocument();
    });

    // Ensure no retry button is shown
    expect(screen.queryByText("Retry")).not.toBeInTheDocument();

    // Ensure we did not retry the 404 request: exactly 2 calls (user + profile)
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});
