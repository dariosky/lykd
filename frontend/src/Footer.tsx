import { ApiStatus } from "./api";

export function Footer(props: {
  loading: boolean;
  error: Error | null;
  apiStatus: ApiStatus | undefined;
}) {
  return (
    <footer className="footer">
      <div className="footer-content">
        {props.loading && (
          <div className="status-indicator loading">
            <span>Connecting to backend...</span>
          </div>
        )}
        {props.error && (
          <div className="status-indicator error">
            <span>Backend connection failed</span>
          </div>
        )}
        {props.apiStatus && (
          <>
            <div className="status-indicator">
              <div className="status-dot"></div>
              <span>Backend: {props.apiStatus.status}</span>
            </div>
            <span>•</span>
            <span>Version: {props.apiStatus.version}</span>
          </>
        )}
      </div>
    </footer>
  );
}
