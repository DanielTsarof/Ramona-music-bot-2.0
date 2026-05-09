from __future__ import annotations

import discord
from discord.ext import commands


class GeneralCog(commands.Cog, name="General"):
    def __init__(self, bot: commands.Bot) -> None:
        self._bot = bot

    @commands.hybrid_command(description="Check bot latency")
    async def ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self._bot.latency * 1000)
        await ctx.send(f"🏓 Pong! Latency: **{latency_ms} ms**")
