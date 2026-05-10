from __future__ import annotations

from pathlib import Path

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_response_tokens: int = 500,
        system_prompt_path: str = "default-system-prompt.txt",
    ) -> None:
        self._system_prompt = Path(system_prompt_path).read_text(encoding="utf-8").strip()
        self._llm = ChatOpenAI(api_key=api_key, model=model, max_tokens=max_response_tokens)

    async def complete(self, context: list[BaseMessage]) -> str:
        messages: list[BaseMessage] = [SystemMessage(content=self._system_prompt)] + context
        response = await self._llm.ainvoke(messages)
        return str(response.content)
