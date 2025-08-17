import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Layout from "./Layout";
import "./ErrorPage.css";

interface ErrorPageProps {
  onGoHome: () => void;
  errorType?: "spotify" | "api" | "network" | "generic";
  customTitle?: string;
  customMessage?: string;
}

function ErrorPage({
  onGoHome,
  errorType = "generic",
  customTitle,
  customMessage,
}: ErrorPageProps) {
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [errorTitle, setErrorTitle] = useState<string>("");
  const [searchParams] = useSearchParams();

  useEffect(() => {
    // Get error message and type from URL parameters
    const urlMessage = searchParams.get("message");
    const urlType = searchParams.get("type") as typeof errorType;

    // Use custom props or determine from URL/type
    const finalErrorType = urlType || errorType;
    const finalMessage =
      customMessage || urlMessage || getDefaultMessage(finalErrorType);
    const finalTitle = customTitle || getDefaultTitle(finalErrorType);

    setErrorMessage(decodeURIComponent(finalMessage));
    setErrorTitle(finalTitle);
  }, [errorType, customTitle, customMessage, searchParams]);

  const getDefaultTitle = (type: string): string => {
    switch (type) {
      case "spotify":
        return "🙉 Spotify Connection Failed";
      case "api":
        return "🫥 Request Failed";
      case "network":
        return "🔌 Network Error";
      default:
        return "🥺 Something Went Wrong";
    }
  };

  const getDefaultMessage = (type: string): string => {
    switch (type) {
      case "spotify":
        return "We encountered an issue while connecting to Spotify";
      case "api":
        return "The server request failed. Please try again later";
      case "network":
        return "Unable to connect to the server. Please check your internet connection";
      default:
        return "An unexpected error occurred";
    }
  };

  const getHelpText = (type: string): JSX.Element => {
    switch (type) {
      case "spotify":
        return (
          <>
            <p>If this problem persists, please check:</p>
            <ul>
              <li>Your internet connection</li>
              <li>Your Spotify account</li>
              <li>That you granted the necessary permissions</li>
              <li>Try logging out and back into Spotify</li>
            </ul>
          </>
        );
      case "api":
        return (
          <>
            <p>If this problem persists, please:</p>
            <ul>
              <li>Refresh the page and try again</li>
              <li>Check your Internet connection</li>
              <li>Contact support if the issue continues</li>
            </ul>
          </>
        );
      case "network":
        return (
          <>
            <p>To resolve this issue:</p>
            <ul>
              <li>Check your Internet connection</li>
              <li>Try refreshing the page</li>
              <li>Disable any VPN or proxy</li>
            </ul>
          </>
        );
      default:
        return (
          <>
            <p>You can try:</p>
            <ul>
              <li>Refreshing the page</li>
              <li>Going back to the home page</li>
              <li>Checking your internet connection</li>
              <li>Trying again in a few minutes</li>
            </ul>
          </>
        );
    }
  };

  const getErrorIcon = (type: string): JSX.Element => {
    switch (type) {
      case "network":
        return (
          <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M3 12h18m-9-9v18" />
            <path d="M8 8l8 8" />
            <path d="M16 8l-8 8" />
          </svg>
        );
      case "api":
        return (
          <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        );
      default:
        return (
          <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        );
    }
  };

  return (
    <Layout>
      <div className="error-page">
        <div className="error-container">
          <div className="error-icon">{getErrorIcon(errorType)}</div>

          <div className="error-content">
            <h1 className="error-title">{errorTitle}</h1>
            <p className="error-message">{errorMessage}</p>

            <div className="error-help">
              {getHelpText(searchParams.get("type") || errorType)}
            </div>

            <div className="error-actions">
              <button onClick={onGoHome} className="home-button">
                Return to Home
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default ErrorPage;
