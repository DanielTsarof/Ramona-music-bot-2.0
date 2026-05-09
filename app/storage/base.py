from typing import Any

from app.storage.meta import meta
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for all models."""

    id: Any
    metadata = meta
