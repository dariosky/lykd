import React from "react";
import { User } from "./api";
import "./Layout.css";

interface UserDropdownProps {
  currentUser: User | null;
  isDropdownOpen: boolean;
  setIsDropdownOpen: (open: boolean) => void;
  isMobile: boolean;
  handlePublicProfileClick: () => void;
  handleSettingsClick: () => void;
  handleIgnoredClick: () => void;
  handleLogout: () => void;
  logoutMutation: { isPending: boolean };
}

const UserDropdown: React.FC<UserDropdownProps> = ({
  currentUser,
  isDropdownOpen,
  setIsDropdownOpen,
  isMobile,
  handlePublicProfileClick,
  handleSettingsClick,
  handleIgnoredClick,
  handleLogout,
  logoutMutation,
}) => {
  return (
    <div className="user-dropdown-container">
      {currentUser ? (
        <button
          className="user-button"
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        >
          <img
            src={currentUser.picture}
            alt={currentUser.name}
            className="user-avatar-small"
          />
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="currentColor"
            className={`dropdown-arrow ${isDropdownOpen ? "open" : ""}`}
          >
            <path d="M7 10l5 5 5-5z" />
          </svg>
        </button>
      ) : (
        <div />
      )}

      {isDropdownOpen && currentUser && (
        <div className="user-dropdown">
          <div className="dropdown-user-info">
            <div className="dropdown-name">{currentUser.name}</div>
            <span className="dropdown-email">{currentUser.email}</span>
          </div>
          {/* On mobile, show public profile button in dropdown */}
          {isMobile && (
            <button
              className="dropdown-item"
              onClick={handlePublicProfileClick}
            >
              {/* Outlined world SVG */}
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M2 12h20" />
                <path d="M12 2a15.3 15.3 0 0 1 0 20" />
                <path d="M12 2a15.3 15.3 0 0 0 0 20" />
              </svg>
              Public Profile
            </button>
          )}
          <div className="dropdown-divider"></div>
          <button className="dropdown-item" onClick={handleSettingsClick}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.5.5 0 0 0 .12-.64l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.028 7.028 0 0 0-1.63-.94l-.36-2.54a.5.5 0 0 0-.5-.42h-3.84a.5.5 0 0 0-.5.42l-.36 2.54c-.58.22-1.13.52-1.63.94l-2.39-.96a.5.5 0 0 0-.6.22L2.75 8.84a.5.5 0 0 0 .12.64l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58a.5.5 0 0 0-.12.64l1.92 3.32c.14.24.43.34.68.22l2.39-.96c.5.41 1.05.72 1.63.94l.36 2.54c.06.25.27.42.5.42h3.84c.25 0 .46-.17.5-.42l.36-2.54c.58-.22 1.13-.52 1.63-.94l2.39.96c.25.12.54.02.68-.22l1.92-3.32a.5.5 0 0 0-.12-.64l-2.03-1.58zM12 15.6a3.6 3.6 0 1 1 0-7.2 3.6 3.6 0 0 1 0 7.2z" />
            </svg>
            Settings
          </button>
          <button className="dropdown-item" onClick={handleIgnoredClick}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
            </svg>
            Ignored Items
          </button>
          <button
            className="dropdown-item logout"
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.59L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" />
            </svg>
            {logoutMutation.isPending ? "Logging out..." : "Logout"}
          </button>
        </div>
      )}
    </div>
  );
};

export default UserDropdown;
