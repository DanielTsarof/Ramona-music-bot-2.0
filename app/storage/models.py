from __future__ import annotations

from datetime import datetime

from app.storage.base import Base
from sqlalchemy import TIMESTAMP, BigInteger, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class IdIntMixin:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)


class Track(Base, IdIntMixin):
    __tablename__ = "tracks"

    video_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    request_count: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    last_requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
