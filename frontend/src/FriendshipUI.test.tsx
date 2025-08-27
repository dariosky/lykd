import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import PublicProfilePage from "./PublicProfilePage";
import Layout from "./Layout";
import { apiService } from "./api";
import { AuthProvider } from "./AuthContext";

function renderWithProviders(ui: React.ReactNode, initialEntries: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter
          initialEntries={initialEntries}
          future={{
            v7_relativeSplatPath: true,
            v7_startTransition: true,
          }}
        >
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
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("Friendship UI", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows Add friend and transitions to Request sent", async () => {
    vi.spyOn(apiService, "getCurrentUser").mockResolvedValueOnce({
      user: {
        id: "me",
        name: "Me",
        email: "me@example.com",
        username: "meuser",
        picture: "",
        join_date: new Date().toISOString(),
        is_admin: false,
      },
    });
    vi.spyOn(apiService, "getPublicProfile").mockResolvedValueOnce({
      user: {
        id: "other",
        name: "Other",
        username: "otheruser",
        picture: null,
        join_date: new Date().toISOString(),
        is_friend: true,
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
    });

    vi.spyOn(apiService, "sendFriendRequest").mockResolvedValueOnce({
      friendship: {
        status: "pending",
        requested_at: new Date().toISOString(),
      },
    });
    vi.spyOn(apiService, "getPendingRequests").mockResolvedValue({
      pending: [],
    });

    renderWithProviders(<PublicProfilePage />, ["/user/otheruser"]);

    // Button appears
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /add friend/i }),
      ).toBeInTheDocument();
    });

    // Click Add friend
    fireEvent.click(screen.getByRole("button", { name: /add friend/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /request sent/i, hidden: true }),
      ).toBeInTheDocument();
    });
  });

  it("shows bell when there are pending friend requests and hides after accept", async () => {
    vi.spyOn(apiService, "getCurrentUser").mockResolvedValueOnce({
      user: {
        id: "me",
        name: "Me",
        email: "me@example.com",
        username: "meuser",
        picture: "",
        join_date: new Date().toISOString(),
        is_admin: false,
      },
    });
    vi.spyOn(apiService, "getPendingRequests")
      .mockResolvedValueOnce({
        pending: [
          {
            user: { id: "u2", name: "Alice", username: "alice", picture: null },
            requested_at: new Date().toISOString(),
          },
        ],
      })
      .mockResolvedValueOnce({ pending: [] });
    vi.spyOn(apiService, "acceptFriendRequest").mockResolvedValueOnce({
      friendship: {
        status: "accepted",
        responded_at: new Date().toISOString(),
      },
    });

    renderWithProviders(
      <Layout>
        <div>Home</div>
      </Layout>,
      ["/"],
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

    fireEvent.click(screen.getByRole("button", { name: /accept/i }));

    // Bell should disappear once list is empty (we allow some time for refetch)
    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: /friend requests/i }),
      ).not.toBeInTheDocument();
    });
  });
});
