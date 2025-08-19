import tomllib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from pydantic import BaseModel

from models.auth import User
from models.common import get_session
from routes.deps import get_current_user
from settings import PROJECT_PATH

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
    user: User | None = Depends(get_current_user),
):
    if not user:
        return {"user": None}

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "username": user.username,
            "picture": user.picture,
            "join_date": user.join_date.isoformat(),
            "is_admin": user.is_admin,
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
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
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
