import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import PublicProfilePage from "./PublicProfilePage";
import Layout from "./Layout";

const mockFetch = vi.fn();
(globalThis as any).fetch = mockFetch;

function renderWithProviders(ui: React.ReactNode, initialEntries: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/user/:username" element={ui} />
          <Route
            path="/"
            element={
              <Layout>
                <div>Home</div>
              </Layout>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Friendship UI", () => {
  beforeEach(() => mockFetch.mockReset());

  it("shows Add friend and transitions to Request sent", async () => {
    // 1) getCurrentUser (logged in)
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        user: {
          id: "me",
          name: "Me",
          email: "me@example.com",
          username: "meuser",
          picture: "",
          join_date: new Date().toISOString(),
          is_admin: false,
        },
      }),
    });
    // 2) getPublicProfile
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        user: {
          id: "other",
          name: "Other",
          username: "otheruser",
          picture: null,
          join_date: new Date().toISOString(),
        },
        stats: {
          total_plays: 0,
          total_likes: 0,
          total_listening_time_sec: 0,
          listening_time_last_30_days_sec: 0,
          tracking_since: null,
        },
        highlights: {
          top_songs_30_days: [],
          top_songs_all_time: [],
          top_artists: [],
          most_played_decade: null,
        },
      }),
    });
    // 3) friendship status = none
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: "none" }),
    });
    // 4) pending list (Layout) — empty
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ pending: [] }),
    });

    renderWithProviders(<PublicProfilePage />, ["/user/otheruser"]);

    // Button appears
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /add friend/i }),
      ).toBeInTheDocument();
    });

    // Click Add friend
    // 5) POST send request
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        friendship: {
          status: "pending",
          requested_at: new Date().toISOString(),
        },
      }),
    });
    // 6) possible refetch of pending list after success (invalidate)
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ pending: [] }),
    });
    // 7) refetch status -> pending_outgoing
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: "pending_outgoing" }),
    });

    fireEvent.click(screen.getByRole("button", { name: /add friend/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /request sent/i }),
      ).toBeInTheDocument();
    });
  });

  it("shows bell when there are pending friend requests and hides after accept", async () => {
    // 1) getCurrentUser for Layout
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        user: {
          id: "me",
          name: "Me",
          email: "me@example.com",
          username: "meuser",
          picture: "",
          join_date: new Date().toISOString(),
          is_admin: false,
        },
      }),
    });
    // 2) pending list with one request
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        pending: [
          {
            user: { id: "u2", name: "Alice", username: "alice", picture: null },
            requested_at: new Date().toISOString(),
          },
        ],
      }),
    });

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <Layout>
            <div>Home</div>
          </Layout>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Bell visible with badge 1
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /friend requests/i }),
      ).toBeInTheDocument();
    });
    const badge = screen.getByText("1");
    expect(badge).toBeInTheDocument();

    // Open dropdown
    fireEvent.click(screen.getByRole("button", { name: /friend requests/i }));
    await waitFor(() => {
      expect(screen.getByText("Alice")).toBeInTheDocument();
    });

    // 3) Accept request -> POST
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        friendship: {
          status: "accepted",
          responded_at: new Date().toISOString(),
        },
      }),
    });
    // 4) Refetch pending -> empty
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ pending: [] }),
    });

    fireEvent.click(screen.getByRole("button", { name: /accept/i }));

    // Bell should disappear once list is empty (we allow some time for refetch)
    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: /friend requests/i }),
      ).not.toBeInTheDocument();
    });
  });
});
