from __future__ import annotations

from app.storage.crud.base_crud import AsyncBaseRepository
from app.storage.models import Context
from sqlalchemy.ext.asyncio import AsyncSession


class ContextRepository(AsyncBaseRepository[Context]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Context)

    async def save_message(
        self,
        channel_id: int,
        role: str,
        content: str,
        author_name: str | None = None,
        tokens: int | None = None,
        model: str | None = None,
    ) -> Context:
        return await self.create(
            Context(
                channel_id=channel_id, role=role, content=content, author_name=author_name, tokens=tokens, model=model
            )
        )

    async def get_channel_messages(self, channel_id: int) -> list[Context]:
        return await self.list(
            where={"channel_id": channel_id},
            order_by=Context.created_at,
            order_dir="asc",
        )

    async def delete_channel_context(self, channel_id: int) -> int:
        return await self.delete_where({"channel_id": channel_id})
