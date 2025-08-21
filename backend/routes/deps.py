from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request, HTTPException
from models.auth import User
from models.common import get_session
from sqlmodel import Session


def get_current_user_id(request: Request) -> str | None:
    return request.session.get("user_id")


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User | None:
    user_id = get_current_user_id(request)
    if not user_id:
        return None
    return session.get(User, user_id)


def current_user(user: User = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def parse_ui_date(before: str | None) -> datetime | None:
    if not before:
        return None
    try:
        # Expect ISO 8601 string
        return datetime.fromisoformat(before.replace("Z", "+00:00"))
    except Exception:
        return None


# Free-text search across fields
def date_range_for_token(tok: str) -> tuple[datetime, datetime] | None:
    try:
        if len(tok) == 4 and tok.isdigit():
            y = int(tok)
            start = datetime(y, 1, 1, tzinfo=timezone.utc)
            end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
            return start, end
        if len(tok) == 7 and tok[:4].isdigit() and tok[4] == "-" and tok[5:7].isdigit():
            y, m = int(tok[:4]), int(tok[5:7])
            start = datetime(y, m, 1, tzinfo=timezone.utc)
            if m == 12:
                end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
            else:
                end = datetime(y, m + 1, 1, tzinfo=timezone.utc)
            return start, end
        if len(tok) == 10 and tok[4] == "-" and tok[7] == "-":
            y, m, d = int(tok[:4]), int(tok[5:7]), int(tok[8:10])
            start = datetime(y, m, d, tzinfo=timezone.utc)
            end = start + timedelta(days=1)
            return start, end
    except Exception:
        return None
    return None
