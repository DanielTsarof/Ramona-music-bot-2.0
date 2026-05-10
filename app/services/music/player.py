from __future__ import annotations

import asyncio
import contextlib
import enum
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import discord
from app.config import config
from app.constants import FFMPEG_BIN, FFMPEG_OPTIONS
from app.logger import log
from discord.ext import commands

IDLE_DISCONNECT_SECONDS = config.IDLE_DISCONNECT_SECONDS
DEFAULT_VOLUME = config.DEFAULT_VOLUME


@dataclass(slots=True, frozen=True)
class QueueEntry:
    video_id: str
    title: str
    file_path: str
    webpage_url: str
    requester_id: int
    duration: int | None


class PlayerState(str, enum.Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"


class GuildPlayer:
    def __init__(self, bot: commands.Bot, guild_id: int) -> None:
        self._bot = bot
        self.guild_id = guild_id
        self.voice: discord.VoiceClient | None = None
        self.text_channel_id: int | None = None
        self.queue: asyncio.Queue[QueueEntry] = asyncio.Queue()
        self.current: QueueEntry | None = None
        self.state: PlayerState = PlayerState.IDLE
        self.volume: float = DEFAULT_VOLUME
        self._next = asyncio.Event()
        self._loop: bool = False
        self._skip_requested: bool = False
        self._replay_entry: QueueEntry | None = None
        self.now_playing_callback: Callable[[QueueEntry], Awaitable[None]] | None = None
        self._player_task = bot.loop.create_task(self._player_loop())

    def attach(self, voice: discord.VoiceClient, text_channel_id: int) -> None:
        self.voice = voice
        self.text_channel_id = text_channel_id

    async def enqueue(self, entry: QueueEntry) -> int:
        await self.queue.put(entry)
        return self.queue.qsize()

    @property
    def loop(self) -> bool:
        return self._loop

    def toggle_loop(self) -> bool:
        self._loop = not self._loop
        return self._loop

    def skip(self) -> bool:
        if self.voice and (self.voice.is_playing() or self.voice.is_paused()):
            self._skip_requested = True
            self.voice.stop()
            return True
        return False

    def pause(self) -> bool:
        if self.voice and self.voice.is_playing():
            self.voice.pause()
            self.state = PlayerState.PAUSED
            return True
        return False

    def resume(self) -> bool:
        if self.voice and self.voice.is_paused():
            self.voice.resume()
            self.state = PlayerState.PLAYING
            return True
        return False

    def set_volume(self, vol: float) -> None:
        self.volume = vol
        source = getattr(self.voice, "source", None)
        if isinstance(source, discord.PCMVolumeTransformer):
            source.volume = vol

    def get_queue_snapshot(self) -> list[QueueEntry]:
        return list(self.queue._queue)[:10]  # type: ignore[attr-defined]

    def clear_queue(self) -> int:
        count = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                count += 1
            except asyncio.QueueEmpty:
                break

        if self.voice and (self.voice.is_playing() or self.voice.is_paused()):
            self._skip_requested = True
            self.voice.stop()
            if self.current is not None:
                count += 1

        return count

    async def shutdown(self, *, disconnect: bool = True) -> None:
        if self.voice and (self.voice.is_playing() or self.voice.is_paused()):
            self.voice.stop()

        self._player_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._player_task

        if disconnect and self.voice and self.voice.is_connected():
            await self.voice.disconnect(force=True)

    async def _player_loop(self) -> None:
        while True:
            self._next.clear()
            self._skip_requested = False

            if self._replay_entry is not None:
                entry = self._replay_entry
                self._replay_entry = None
                from_queue = False
            else:
                try:
                    entry = await asyncio.wait_for(self.queue.get(), timeout=IDLE_DISCONNECT_SECONDS)
                except asyncio.TimeoutError:
                    log.info(f"Guild {self.guild_id}: idle timeout — disconnecting")
                    if self.voice and self.voice.is_connected():
                        await self.voice.disconnect(force=True)
                    return
                from_queue = True

            self.current = entry
            self.state = PlayerState.PLAYING

            if self.voice is None or not self.voice.is_connected():
                log.warning(f"Guild {self.guild_id}: no voice connection, skipping {entry.title!r}")
                if from_queue:
                    self.queue.task_done()
                self.current = None
                self.state = PlayerState.IDLE
                continue

            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(entry.file_path, executable=FFMPEG_BIN, options=FFMPEG_OPTIONS),
                volume=self.volume,
            )

            def _after(error: Exception | None) -> None:
                if error:
                    log.error(f"Guild {self.guild_id}: playback error — {error}")
                self._bot.loop.call_soon_threadsafe(self._next.set)

            self.voice.play(source, after=_after)
            log.info(f"Guild {self.guild_id}: playing {entry.title!r} ({entry.video_id})")

            if self.now_playing_callback:
                await self.now_playing_callback(entry)

            await self._next.wait()

            self.current = None
            self.state = PlayerState.IDLE
            if from_queue:
                self.queue.task_done()

            if self._loop and not self._skip_requested:
                self._replay_entry = entry


class PlayerRegistry:
    def __init__(self, bot: commands.Bot) -> None:
        self._bot = bot
        self._players: dict[int, GuildPlayer] = {}

    def get_or_create(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self._players:
            self._players[guild_id] = GuildPlayer(self._bot, guild_id)
        return self._players[guild_id]

    def remove(self, guild_id: int) -> GuildPlayer | None:
        return self._players.pop(guild_id, None)

    async def shutdown_all(self) -> None:
        for player in list(self._players.values()):
            await player.shutdown()
        self._players.clear()
