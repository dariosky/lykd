from typing import Optional

from fastapi import Depends, Request
from models.auth import User
from models.common import get_session
from sqlmodel import Session


def get_current_user_id(request: Request) -> Optional[str]:
    return request.session.get("user_id")


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> Optional[User]:
    user_id = get_current_user_id(request)
    if not user_id:
        return None
    return session.get(User, user_id)
