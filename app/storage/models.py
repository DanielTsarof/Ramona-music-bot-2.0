from uuid import UUID

from app.database.base_class import Base  # noqa
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
    sql,
)
from sqlalchemy.orm import Mapped, mapped_column


class IdIntMixin:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
