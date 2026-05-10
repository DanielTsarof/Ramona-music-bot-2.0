from __future__ import annotations

import discord
from app.config import config
from app.logger import log
from app.services.speech.context_service import ContextService
from app.services.speech.llm_client import LLMClient
from discord.ext import commands


class SpeechCog(commands.Cog, name="Speech"):
    def __init__(self, bot: commands.Bot, llm_client: LLMClient, context_service: ContextService) -> None:
        self._bot = bot
        self._llm = llm_client
        self._ctx_svc = context_service

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        if self._bot.user is None or self._bot.user not in message.mentions:
            return

        bot_id = self._bot.user.id
        content = message.content.replace(f"<@{bot_id}>", "").replace(f"<@!{bot_id}>", "").strip()

        if not content:
            return

        channel_id = message.channel.id
        author_name = message.author.display_name

        async with message.channel.typing():
            try:
                await self._ctx_svc.add_user_message(channel_id, content, author_name)
                context = await self._ctx_svc.get_context(channel_id, config.LLM_MAX_TOKENS, config.LLM_MODEL)
                reply = await self._llm.complete(context)
                await self._ctx_svc.add_assistant_message(channel_id, reply)
            except Exception as exc:
                log.exception(f"SpeechCog error in channel {channel_id}: {exc}")
                await message.channel.send("❌ Сорян, не в настроении болтать")
                return

        for i in range(0, len(reply), 2000):
            await message.channel.send(reply[i : i + 2000])
