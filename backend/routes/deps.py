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
