"""Authentication models"""

import datetime
from typing import Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
from .common import CamelModel


class User(SQLModel, CamelModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    picture: str | None = None
    tokens: Dict[str, Any] | None = Field(default_factory=dict, sa_column=Column(JSON))
    join_date: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    is_admin: bool = False

    def get_access_token(self) -> str:
        return self.tokens.get("access_token") if self.tokens else None

    def get_refresh_token(self) -> str:
        return self.tokens.get("refresh_token") if self.tokens else None

    def __str__(self):
        return self.email
