from __future__ import annotations

import discord
from discord.ext import commands

from app.logger import log
from app.schemas.music import TrackInfo
from app.services.music.player import GuildPlayer, PlayerRegistry, PlayerState, QueueEntry
from app.services.music.youtube_music.service import YoutubeMusicService


def _fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return "?"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


class MusicCog(commands.Cog, name="Music"):
    def __init__(self, bot: commands.Bot, music_service: YoutubeMusicService) -> None:
        self._bot = bot
        self._music_service = music_service
        self._registry = PlayerRegistry(bot)

    async def cog_unload(self) -> None:
        await self._registry.shutdown_all()

    async def _ensure_voice(self, ctx: commands.Context) -> discord.VoiceClient:
        if ctx.guild is None:
            raise commands.NoPrivateMessage("Voice commands only work in a server.")

        author = ctx.author
        if not isinstance(author, discord.Member) or not author.voice or not author.voice.channel:
            raise commands.CommandError("You need to be in a voice channel first.")

        channel = author.voice.channel
        me = ctx.guild.me
        if me is None:
            raise commands.CommandError("Could not determine the bot's guild member.")

        perms = channel.permissions_for(me)
        if not perms.connect or not perms.speak:
            raise commands.BotMissingPermissions(["connect", "speak"])

        if ctx.voice_client is None:
            voice = await channel.connect(reconnect=True)
        elif ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)
            voice = ctx.voice_client
        else:
            voice = ctx.voice_client

        player = self._registry.get_or_create(ctx.guild.id)
        player.attach(voice, ctx.channel.id)
        return voice  # type: ignore[return-value]

    @commands.hybrid_command(description="Connect the bot to your voice channel")
    async def join(self, ctx: commands.Context) -> None:
        voice = await self._ensure_voice(ctx)
        await ctx.send(f"🔊 Connected to **{voice.channel}**")

    @commands.hybrid_command(description="Play a YouTube URL or search query")
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        await ctx.defer()

        # Validate before download so the user gets an error immediately
        if ctx.guild is None:
            raise commands.NoPrivateMessage("Voice commands only work in a server.")
        author = ctx.author
        if not isinstance(author, discord.Member) or not author.voice or not author.voice.channel:
            raise commands.CommandError("You need to be in a voice channel first.")

        try:
            track_info: TrackInfo = await self._music_service.get_or_download(query)
        except Exception as exc:
            log.error(f"get_or_download failed for query={query!r}: {exc}")
            await ctx.send(f"❌ Could not load track: {exc}")
            return

        # Connect after download: the player's idle timer starts only when the track is ready
        await self._ensure_voice(ctx)

        player = self._registry.get_or_create(ctx.guild.id)
        entry = QueueEntry(
            video_id=track_info.video_id,
            title=track_info.title,
            file_path=track_info.file_path,
            webpage_url=track_info.webpage_url,
            requester_id=ctx.author.id,
            duration=track_info.duration,
        )
        position = await player.enqueue(entry)
        cache_tag = " *(cached)*" if track_info.from_cache else ""

        if player.current is None and position == 1:
            await ctx.send(f"▶️ Starting: **{entry.title}**{cache_tag}")
        else:
            await ctx.send(f"➕ Queued at position {position}: **{entry.title}**{cache_tag}")

    @commands.hybrid_command(description="Skip the current track")
    async def skip(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self._registry.get_or_create(ctx.guild.id)
        if player.skip():
            await ctx.send("⏭️ Skipped")
        else:
            await ctx.send("Nothing is playing.")

    @commands.hybrid_command(description="Pause playback")
    async def pause(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self._registry.get_or_create(ctx.guild.id)
        if player.pause():
            await ctx.send("⏸️ Paused")
        else:
            await ctx.send("Nothing is playing.")

    @commands.hybrid_command(description="Resume playback")
    async def resume(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self._registry.get_or_create(ctx.guild.id)
        if player.resume():
            await ctx.send("▶️ Resumed")
        else:
            await ctx.send("Not paused.")

    @commands.hybrid_command(description="Set volume (0–200%)")
    async def volume(self, ctx: commands.Context, percent: commands.Range[int, 0, 200]) -> None:
        if ctx.guild is None:
            return
        player = self._registry.get_or_create(ctx.guild.id)
        player.set_volume(percent / 100.0)
        await ctx.send(f"🔉 Volume: **{percent}%**")

    @commands.hybrid_command(name="queue", description="Show the current queue")
    async def show_queue(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self._registry.get_or_create(ctx.guild.id)

        lines: list[str] = []
        if player.current:
            dur = _fmt_duration(player.current.duration)
            state = "⏸️" if player.state == PlayerState.PAUSED else "▶️"
            lines.append(f"{state} **{player.current.title}** `[{dur}]`")

        for i, entry in enumerate(player.get_queue_snapshot(), start=1):
            dur = _fmt_duration(entry.duration)
            lines.append(f"`{i}.` {entry.title} `[{dur}]`")

        await ctx.send("\n".join(lines) if lines else "The queue is empty.")

    @commands.hybrid_command(name="np", description="Show the currently playing track")
    async def now_playing(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self._registry.get_or_create(ctx.guild.id)
        if player.current is None:
            await ctx.send("Nothing is playing right now.")
            return
        entry = player.current
        dur = _fmt_duration(entry.duration)
        state = "⏸️ Paused" if player.state == PlayerState.PAUSED else "▶️ Playing"
        await ctx.send(f"{state}: **{entry.title}** `[{dur}]`\n{entry.webpage_url}")

    @commands.hybrid_command(description="Disconnect the bot and clear the queue")
    async def leave(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self._registry.remove(ctx.guild.id)
        if player:
            await player.shutdown()
            await ctx.send("👋 Disconnected and cleared the queue.")
        elif ctx.voice_client:
            await ctx.voice_client.disconnect(force=True)
            await ctx.send("👋 Disconnected.")
        else:
            await ctx.send("Not in a voice channel.")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if self._bot.user is None or member.id != self._bot.user.id:
            return
        if after.channel is None:
            player = self._registry.remove(member.guild.id)
            if player:
                log.info(f"Guild {member.guild.id}: bot disconnected externally — cleaning up player")
                await player.shutdown(disconnect=False)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"❌ Missing permissions: `{', '.join(error.missing_permissions)}`")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(str(error))
        elif isinstance(error, commands.CommandError) and not isinstance(error, commands.CommandInvokeError):
            await ctx.send(f"❌ {error}")
        elif isinstance(error, commands.CommandInvokeError):
            log.exception(f"Unhandled error in command {ctx.command}", exc_info=error.original)
            await ctx.send(f"❌ Internal error: `{error.original}`")
        else:
            await ctx.send(f"❌ {error}")
