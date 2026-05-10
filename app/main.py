from __future__ import annotations

import asyncio

import discord
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from app.cogs.general import GeneralCog
from app.cogs.music import MusicCog
from app.cogs.speech import SpeechCog
from app.config import config
from app.logger import log
from app.services.music.youtube_music.api_client import YouTubeAPIClient
from app.services.music.youtube_music.service import YoutubeMusicService
from app.services.music.youtube_music.ytdl import YtDlpDownloader
from app.services.speech.context_service import ContextService
from app.services.speech.llm_client import LLMClient
from app.storage.session import SessionLocal
from app.utils.file_storage import LocalFileStorage
from discord.ext import commands


def run_migrations() -> None:
    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_command.upgrade(alembic_cfg, "head")
    log.info("Database migrations applied")


async def main() -> None:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    api_client = YouTubeAPIClient(config.YOUTUBE_TOKEN)
    file_storage = LocalFileStorage(config.STORAGE_PATH)
    downloader = YtDlpDownloader(file_storage)
    music_service = YoutubeMusicService(api_client, downloader, SessionLocal)
    llm_client = LLMClient(config.LLM_API_KEY, config.LLM_MODEL, config.LLM_MAX_RESPONSE_TOKENS)
    context_service = ContextService(SessionLocal, config.LLM_MODEL)

    @bot.event
    async def on_ready() -> None:
        log.info(f"Logged in as {bot.user} (id={bot.user.id})")
        try:
            synced = await bot.tree.sync()
            log.info(f"Synced {len(synced)} slash command(s)")
        except Exception as exc:
            log.error(f"Failed to sync slash commands: {exc}")

    async with bot:
        await bot.add_cog(MusicCog(bot, music_service))
        await bot.add_cog(GeneralCog(bot))
        await bot.add_cog(SpeechCog(bot, llm_client, context_service))
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    run_migrations()
    asyncio.run(main())
