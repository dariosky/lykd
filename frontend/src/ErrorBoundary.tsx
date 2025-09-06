import React from "react";

type ErrorBoundaryProps = {
  children: React.ReactNode;
  fallback?:
    | React.ReactNode
    | ((args: { error: Error; reset: () => void }) => React.ReactNode);
  resetKeys?: unknown[];
};

type ErrorBoundaryState = {
  hasError: boolean;
  error?: Error;
};

function arraysAreEqual(a?: unknown[], b?: unknown[]) {
  if (a === b) return true;
  if (!a || !b || a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

export default class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false, error: undefined };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Basic logging; replace with your telemetry if needed
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    if (
      this.state.hasError &&
      !arraysAreEqual(this.props.resetKeys, prevProps.resetKeys)
    ) {
      this.reset();
    }
  }

  reset = () => this.setState({ hasError: false, error: undefined });

  render() {
    if (this.state.hasError) {
      const { fallback } = this.props;
      if (typeof fallback === "function" && this.state.error) {
        return fallback({ error: this.state.error, reset: this.reset });
      }
      if (fallback) return <>{fallback}</>;

      return (
        <div
          style={{
            padding: 24,
            margin: 16,
            borderRadius: 12,
            background: "#1f2937",
            color: "#e5e7eb",
            border: "1px solid #374151",
          }}
          role="alert"
          aria-live="assertive"
        >
          <h2 style={{ margin: 0, fontSize: 18 }}>Something went wrong</h2>
          <p style={{ marginTop: 8, opacity: 0.9 }}>
            We hit an unexpected error while rendering this page.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              onClick={this.reset}
              style={{
                padding: "6px 12px",
                borderRadius: 8,
                border: "1px solid #4b5563",
                background: "#111827",
                color: "#e5e7eb",
                cursor: "pointer",
              }}
            >
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: "6px 12px",
                borderRadius: 8,
                border: "1px solid transparent",
                background: "#2563eb",
                color: "white",
                cursor: "pointer",
              }}
            >
              Reload page
            </button>
          </div>
          {import.meta.env.MODE !== "production" && this.state.error && (
            <pre
              style={{
                marginTop: 12,
                padding: 12,
                background: "#111827",
                borderRadius: 8,
                overflow: "auto",
                maxHeight: 240,
                fontSize: 12,
                lineHeight: 1.4,
              }}
            >
              {(this.state.error.stack || this.state.error.message) ?? ""}
            </pre>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
