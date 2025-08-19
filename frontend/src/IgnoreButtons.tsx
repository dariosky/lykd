import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiService, queryKeys } from "./api";
import "./IgnoreButtons.css";

interface IgnoreTrackButtonProps {
  trackId: string;
  title?: string;
  className?: string;
}

export function IgnoreTrackButton({
  trackId,
  title = "Ignore from stats",
  className = "",
}: IgnoreTrackButtonProps) {
  const queryClient = useQueryClient();

  const ignoreMutation = useMutation({
    mutationFn: () => apiService.ignoreTrack(trackId),
    onSuccess: () => {
      // Invalidate relevant queries to refresh data across the app
      queryClient.invalidateQueries({ queryKey: queryKeys.ignored });
      // Invalidate all recent queries (any filters)
      queryClient.invalidateQueries({ queryKey: ["recent"] });
      // Invalidate any public profiles in view
      queryClient.invalidateQueries({ queryKey: ["publicProfile"] });
    },
  });

  return (
    <button
      className={`ignore-btn ${className}`}
      onClick={(e) => {
        e.stopPropagation();
        ignoreMutation.mutate();
      }}
      disabled={ignoreMutation.isPending}
      title={title}
      aria-label={title}
    >
      {ignoreMutation.isPending ? "..." : "🚫"}
    </button>
  );
}

interface IgnoreArtistButtonProps {
  artistId: string;
  artistName: string;
  title?: string;
  className?: string;
}

export function IgnoreArtistButton({
  artistId,
  artistName,
  title = `Ignore from stats`,
  className = "",
}: IgnoreArtistButtonProps) {
  const queryClient = useQueryClient();

  const ignoreMutation = useMutation({
    mutationFn: () => apiService.ignoreArtist(artistId),
    onSuccess: () => {
      // Invalidate relevant queries to refresh data across the app
      queryClient.invalidateQueries({ queryKey: queryKeys.ignored });
      // Invalidate all recent queries (any filters)
      queryClient.invalidateQueries({ queryKey: ["recent"] });
      // Invalidate any public profiles in view
      queryClient.invalidateQueries({ queryKey: ["publicProfile"] });
    },
  });

  const displayTitle = title ?? `Ignore ${artistName} from stats`;

  return (
    <button
      className={`ignore-btn ${className}`}
      onClick={(e) => {
        e.stopPropagation();
        ignoreMutation.mutate();
      }}
      disabled={ignoreMutation.isPending}
      title={displayTitle}
      aria-label={displayTitle}
    >
      {ignoreMutation.isPending ? "..." : "🚫"}
    </button>
  );
}

interface UnignoreTrackButtonProps {
  trackId: string;
  title?: string;
  className?: string;
}

export function UnignoreTrackButton({
  trackId,
  title = "Add back to stats",
  className = "",
}: UnignoreTrackButtonProps) {
  const queryClient = useQueryClient();

  const unignoreMutation = useMutation({
    mutationFn: () => apiService.unignoreTrack(trackId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ignored });
      queryClient.invalidateQueries({ queryKey: ["recent"] });
      queryClient.invalidateQueries({ queryKey: ["publicProfile"] });
    },
  });

  return (
    <button
      className={`unignore-btn ${className}`}
      onClick={(e) => {
        e.stopPropagation();
        unignoreMutation.mutate();
      }}
      disabled={unignoreMutation.isPending}
      title={title}
      aria-label={title}
    >
      {unignoreMutation.isPending ? (
        "..."
      ) : (
        <>
          <span className="btn-icon">✓</span>
          <span className="btn-label">Unignore</span>
        </>
      )}
    </button>
  );
}

interface UnignoreArtistButtonProps {
  artistId: string;
  artistName: string;
  title?: string;
  className?: string;
}

export function UnignoreArtistButton({
  artistId,
  artistName,
  title = "Add back to stats",
  className = "",
}: UnignoreArtistButtonProps) {
  const queryClient = useQueryClient();

  const unignoreMutation = useMutation({
    mutationFn: () => apiService.unignoreArtist(artistId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ignored });
      queryClient.invalidateQueries({ queryKey: ["recent"] });
      queryClient.invalidateQueries({ queryKey: ["publicProfile"] });
    },
  });

  const displayTitle = title ?? `add ${artistName} back to the stats`;

  return (
    <button
      className={`unignore-btn ${className}`}
      onClick={(e) => {
        e.stopPropagation();
        unignoreMutation.mutate();
      }}
      disabled={unignoreMutation.isPending}
      title={displayTitle}
      aria-label={displayTitle}
    >
      {unignoreMutation.isPending ? (
        "..."
      ) : (
        <>
          <span className="btn-icon">✓</span>
          <span className="btn-label">Unignore</span>
        </>
      )}
    </button>
  );
}

// New: Report buttons
export function ReportTrackButton({
  trackId,
  title = "Request global ignore",
  className = "",
}: {
  trackId: string;
  title?: string;
  className?: string;
}) {
  const queryClient = useQueryClient();
  const reportMutation = useMutation({
    mutationFn: () => apiService.reportTrack(trackId),
    onSuccess: () => {
      // Refresh reports for admins if open and the ignored list to reflect reported state
      queryClient.invalidateQueries({ queryKey: queryKeys.reports });
      queryClient.invalidateQueries({ queryKey: queryKeys.ignored });
    },
  });
  return (
    <button
      className={`report-btn ${className}`}
      onClick={(e) => {
        e.stopPropagation();
        reportMutation.mutate();
      }}
      disabled={reportMutation.isPending}
      title={title}
      aria-label={title}
    >
      {reportMutation.isPending ? (
        "..."
      ) : (
        <>
          <span className="btn-icon">📣</span>
          <span className="btn-label">Report</span>
        </>
      )}
    </button>
  );
}

export function ReportArtistButton({
  artistId,
  artistName,
  title = "Request global ignore",
  className = "",
}: {
  artistId: string;
  artistName: string;
  title?: string;
  className?: string;
}) {
  const queryClient = useQueryClient();
  const reportMutation = useMutation({
    mutationFn: () => apiService.reportArtist(artistId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports });
      queryClient.invalidateQueries({ queryKey: queryKeys.ignored });
    },
  });
  const displayTitle = title ?? `Request to ignore ${artistName} globally`;
  return (
    <button
      className={`report-btn ${className}`}
      onClick={(e) => {
        e.stopPropagation();
        reportMutation.mutate();
      }}
      disabled={reportMutation.isPending}
      title={displayTitle}
      aria-label={displayTitle}
    >
      {reportMutation.isPending ? (
        "..."
      ) : (
        <>
          <span className="btn-icon">📣</span>
          <span className="btn-label">Report</span>
        </>
      )}
    </button>
  );
}
