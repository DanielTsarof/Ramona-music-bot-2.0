from __future__ import annotations

import tiktoken
from app.storage.crud.context_crud import ContextRepository
from app.storage.models import Context
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import async_sessionmaker


def _count_tokens(text: str, model: str) -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


class ContextService:
    def __init__(self, session_factory: async_sessionmaker, model: str) -> None:
        self._session_factory = session_factory
        self._model = model

    async def add_user_message(self, channel_id: int, content: str, author_name: str) -> None:
        prefixed = f"{author_name}: {content}"
        tokens = _count_tokens(prefixed, self._model)
        async with self._session_factory() as session:
            repo = ContextRepository(session)
            await repo.save_message(channel_id, "user", prefixed, author_name, tokens, self._model)

    async def add_assistant_message(self, channel_id: int, content: str) -> None:
        tokens = _count_tokens(content, self._model)
        async with self._session_factory() as session:
            repo = ContextRepository(session)
            await repo.save_message(channel_id, "assistant", content, tokens=tokens, model=self._model)

    async def get_context(self, channel_id: int, max_tokens: int, model: str) -> list[BaseMessage]:
        async with self._session_factory() as session:
            repo = ContextRepository(session)
            rows = await repo.get_channel_messages(channel_id)

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")

        budget = max_tokens
        kept: list[Context] = []
        for row in reversed(rows):
            tokens = row.tokens if row.tokens is not None else len(enc.encode(row.content))
            if tokens > budget:
                break
            budget -= tokens
            kept.append(row)

        kept.reverse()
        return [HumanMessage(content=r.content) if r.role == "user" else AIMessage(content=r.content) for r in kept]

    async def clear_channel(self, channel_id: int) -> None:
        async with self._session_factory() as session:
            repo = ContextRepository(session)
            await repo.delete_channel_context(channel_id)
