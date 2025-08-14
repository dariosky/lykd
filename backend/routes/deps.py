from fastapi import Depends, Request
from sqlmodel import Session
from typing import Optional

from models.auth import User
from models.common import get_session
from sqlmodel import select


def get_current_user_id(request: Request) -> Optional[str]:
    return request.session.get("user_id")


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> Optional[User]:
    user_id = get_current_user_id(request)
    if not user_id:
        return None
    return session.get(User, user_id)


def generate_unique_username(base: str, session: Session) -> str:
    base = (base or "").strip()
    if not base:
        base = "user"
    candidate = base
    suffix = 2
    while session.exec(select(User).where(User.username == candidate)).first():
        candidate = f"{base}#{suffix}"
        suffix += 1
    return candidate
