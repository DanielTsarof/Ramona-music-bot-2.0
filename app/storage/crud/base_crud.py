from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Generic, Literal, TypeVar

from app.storage.base import Base
from pydantic import BaseModel
from sqlalchemy import and_, asc, delete, desc, insert, select, tuple_, update
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    InstrumentedAttribute,
    Load,
    selectinload,
)
from sqlalchemy.sql import ColumnElement
from sqlalchemy.sql.selectable import Select

T = TypeVar("T", bound=Base)


class AsyncBaseRepository(Generic[T]):
    """
    The basic async repository for SQLAlchemy DeclarativeBase (SQLAlchemy 2.x).

    Supports:
      - where as dict -> AND(field == value, ...)
      - eager loading via selectinload (pass relationship attributes) or ready-made Load options
      - pagination via fastapi-pagination.ext.sqlalchemy.paginate
    """

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    # helpers
    def _build_where(self, where: Any) -> ColumnElement[bool] | None:
        if where is None:
            return None

        if isinstance(where, Mapping):
            conditions: list[ColumnElement[bool]] = []
            for k, v in where.items():
                if not hasattr(self.model, k):
                    raise AttributeError(f"{self.model.__name__} has no attribute '{k}'")
                conditions.append(getattr(self.model, k) == v)
            return and_(*conditions) if conditions else None
        return where

    def _build_load_options(self, load: Iterable[Load | InstrumentedAttribute] | None) -> list[Load]:
        if not load:
            return []

        options: list[Load] = []
        for option in load:
            if isinstance(option, Load):
                options.append(option)
            else:
                options.append(selectinload(option))
        return options

    def _normalize_order_dir(self, order_dir: str) -> Literal["asc", "desc"]:
        return "asc" if str(order_dir).lower() == "asc" else "desc"

    def _to_values(self, obj: Any) -> dict[str, Any]:
        """
        Causes the object to be dict for insert/update:
          - pydantic BaseModel -> model_dump(exclude_unset=True, exclude_none=True)
          - Mapping -> dict(obj)
          - ORM instance -> po column attributes (without links)
        """
        if isinstance(obj, BaseModel):
            return obj.model_dump(exclude_unset=True, exclude_none=True)

        if isinstance(obj, Mapping):
            return dict(obj)

        # ORM Instance
        mapper = sa_inspect(obj).mapper
        data: dict[str, Any] = {}
        for attr in mapper.column_attrs:
            key = attr.key
            data[key] = getattr(obj, key)
        return data

    def _pk_keys(self) -> list[str]:
        mapper = sa_inspect(self.model)
        return [col.key for col in mapper.primary_key]

    def _pk_identity_from_obj(self, obj: T) -> tuple[Any, ...]:
        keys = self._pk_keys()
        return tuple(getattr(obj, k) for k in keys)

    async def _fetch_by_pks(self, pks: list[tuple[Any, ...]]) -> list[T]:
        if not pks:
            return []

        keys = self._pk_keys()
        if len(keys) == 1:
            col = getattr(self.model, keys[0])
            stmt = select(self.model).where(col.in_([pk[0] for pk in pks]))
        else:
            cols = [getattr(self.model, k) for k in keys]
            stmt = select(self.model).where(tuple_(*cols).in_(pks))

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # keep the same order as pks (DB IN() order is not guaranteed)
        by_pk = {self._pk_identity_from_obj(r): r for r in rows}
        return [by_pk[pk] for pk in pks if pk in by_pk]

    def _prepare_insert_values(self, obj: Any) -> dict[str, Any]:
        """
        Like _to_values(), but avoids sending explicit NULL for:
          - PKs (autoincrement / server-generated)
          - columns with Python/default or server_default
        so DB defaults can kick in.
        """
        data = self._to_values(obj)

        mapper = sa_inspect(self.model)
        for col in mapper.local_table.columns:
            key = col.key
            if key not in data:
                continue
            if data[key] is None and (
                col.primary_key
                or col.autoincrement is True
                or col.default is not None
                or col.server_default is not None
            ):
                data.pop(key, None)

        return data

    # read
    async def get(
        self,
        entity_id: Any,
        load: Iterable[Load | InstrumentedAttribute] | None = None,
        populate_existing: bool = False,
    ) -> T | None:
        options = self._build_load_options(load)
        return await self.session.get(
            self.model,
            entity_id,
            options=options or None,
            populate_existing=populate_existing,
        )

    async def list(
        self,
        where: Any = None,
        load: Iterable[Load | InstrumentedAttribute] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        order_by: InstrumentedAttribute | ColumnElement | None = None,
        order_dir: Literal["asc", "desc"] = "desc",
    ) -> list[T]:
        statement: Select[Any] = select(self.model)

        for option in self._build_load_options(load):
            statement = statement.options(option)

        cond = self._build_where(where)
        if cond is not None:
            statement = statement.where(cond)

        if order_by is not None:
            direction = self._normalize_order_dir(order_dir)
            statement = statement.order_by(desc(order_by) if direction == "desc" else asc(order_by))

        if offset is not None:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)

        result = await self.session.execute(statement)
        return result.scalars().all()

    async def first(
        self,
        where: Any,
        load: Iterable[Load | InstrumentedAttribute] | None = None,
        order_by: InstrumentedAttribute | ColumnElement | None = None,
        order_dir: Literal["asc", "desc"] = "desc",
    ) -> T | None:
        statement: Select[Any] = select(self.model)

        for option in self._build_load_options(load):
            statement = statement.options(option)

        cond = self._build_where(where)
        if cond is not None:
            statement = statement.where(cond)

        if order_by is not None:
            direction = self._normalize_order_dir(order_dir)
            statement = statement.order_by(desc(order_by) if direction == "desc" else asc(order_by))

        statement = statement.limit(1)
        result = await self.session.execute(statement)
        return result.scalars().first()

    # write
    async def create(self, obj: T) -> T:
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: T) -> T:
        obj = await self.session.merge(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update_and_get_relations(self, obj: T, load_options: Iterable[Load] | None = None) -> T:
        """
        Commits the current changes and then re-reads the PK entity with download options.
        It is useful when you want to return an entity along with relations after an update.
        """
        try:
            await self.session.flush()
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        mapper = sa_inspect(self.model)
        pk_columns = [col.key for col in mapper.primary_key]
        pk_values = {col: getattr(obj, col) for col in pk_columns}

        stmt = select(self.model).where(*[getattr(self.model, col) == value for col, value in pk_values.items()])

        if load_options:
            stmt = stmt.options(*list(load_options))

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_where(self, where: Any, values: dict[str, Any]) -> int:
        cond = self._build_where(where)
        if cond is None:
            raise ValueError("update_where(): 'where' is required (refusing to update all rows).")

        stmt = update(self.model).where(cond).values(**values).execution_options(synchronize_session="fetch")
        result = await self.session.execute(stmt)
        await self.session.commit()
        return int(result.rowcount or 0)

    async def delete(self, entity_id: Any) -> None:
        obj = await self.get(entity_id)
        if obj is not None:
            await self.session.delete(obj)
            await self.session.commit()

    async def delete_where(self, where: Any) -> int:
        cond = self._build_where(where)
        if cond is None:
            raise ValueError("delete_where(): 'where' is required (refusing to delete all rows).")

        stmt = delete(self.model).where(cond)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return int(result.rowcount or 0)

    async def insert_many(
        self,
        objs: Iterable[T | Mapping[str, Any] | BaseModel],
        *,
        use_core_insert: bool = True,
    ) -> list[T]:
        items = list(objs)
        if not items:
            return []

        values = [self._prepare_insert_values(x) for x in items]

        if use_core_insert:
            try:
                stmt = insert(self.model).returning(self.model)
                result = await self.session.execute(stmt, values)
                inserted = result.scalars().all()
                await self.session.commit()
                return inserted
            except Exception:
                await self.session.rollback()
                # fall through to ORM path (still no refresh loop)

        # ORM path (supports cascades). Still avoid refresh-per-row:
        # flush to get PKs, commit, then bulk SELECT by PKs once.
        orm_objs: list[T]
        if all(isinstance(x, self.model) for x in items):
            orm_objs = list(items)  # type: ignore[assignment]
        else:
            orm_objs = [self.model(**v) for v in values]

        self.session.add_all(orm_objs)
        try:
            await self.session.flush()
            pks = [self._pk_identity_from_obj(o) for o in orm_objs]
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self._fetch_by_pks(pks)

    async def update_many(self, objs: Sequence[dict[str, Any]]) -> int:
        """
        Bulk update as in SQLAlchemy:
          session.execute(update(Model), [{"id": 1, "field": "x"}, {"id": 2, "field": "y"}])

        Important: each dict should usually contain PK fields (for example, id), otherwise SQLAlchemy
        won't understand which lines to update.
        """
        if not objs:
            return 0

        try:
            result = await self.session.execute(update(self.model), list(objs))
            await self.session.commit()
            return int(result.rowcount or 0)
        except Exception:
            await self.session.rollback()
            raise
