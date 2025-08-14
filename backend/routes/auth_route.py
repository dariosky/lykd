import tomllib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from pydantic import BaseModel

from models.auth import User
from models.common import get_session
from settings import PROJECT_PATH
from .deps import get_current_user

router = APIRouter()


def get_version() -> str:
    with open(PROJECT_PATH / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["version"]


@router.get("/")
async def index():
    return {"version": get_version(), "status": "ok"}


@router.get("/user/me")
async def get_current_user_info(
    current_user: User | None = Depends(get_current_user),
):
    if not current_user:
        return {"user": None}

    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "username": current_user.username,
            "picture": current_user.picture,
            "join_date": current_user.join_date.isoformat(),
            "is_admin": current_user.is_admin,
        }
    }


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}


class UsernameUpdate(BaseModel):
    username: str


@router.post("/user/username")
async def set_username(
    payload: UsernameUpdate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    desired = (payload.username or "").strip()
    if not desired:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if len(desired) > 40:
        raise HTTPException(status_code=400, detail="Username too long")

    existing = session.exec(select(User).where(User.username == desired)).first()

    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=409, detail="Username already taken")

    db_user = session.get(User, current_user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.username = desired
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return {
        "user": {
            "id": db_user.id,
            "name": db_user.name,
            "email": db_user.email,
            "username": db_user.username,
            "picture": db_user.picture,
            "join_date": db_user.join_date.isoformat(),
            "is_admin": db_user.is_admin,
        }
    }
