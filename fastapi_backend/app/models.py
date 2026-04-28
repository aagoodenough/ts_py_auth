from datetime import datetime
from typing import Optional

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    __allow_unmapped__ = True
    
    google_id: Optional[str] = Column(String, nullable=True, unique=True, index=True)
    github_id: Optional[str] = Column(String, nullable=True, unique=True, index=True)
    oauth_email: Optional[str] = Column(String, nullable=True)
    is_oauth_user: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_oauth={self.is_oauth_user})>"