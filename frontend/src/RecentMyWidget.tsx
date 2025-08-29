import { useNavigate } from "react-router-dom";
import { RecentActivityWidget } from "./RecentActivity";

interface RecentMyWidgetProps {
  myIdent: string;
}

export function RecentMyWidget({ myIdent }: RecentMyWidgetProps) {
  const navigate = useNavigate();
  return (
    <div className="dashboard-card">
      <div className="card-header">
        <h2
          className="link"
          onClick={() =>
            navigate(`/recent?user=${encodeURIComponent(myIdent)}`)
          }
        >
          Your Recent Activity
        </h2>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="#1db954">
          <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" />
        </svg>
      </div>
      <div className="card-content">
        <RecentActivityWidget
          includeMe={true}
          filterUser={myIdent}
          className="compact"
        />
      </div>
    </div>
  );
}
