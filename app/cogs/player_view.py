from __future__ import annotations

import discord
from app.services.music.player import GuildPlayer, PlayerState


def _fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return "?"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def build_embed(player: GuildPlayer) -> discord.Embed:
    entry = player.current
    if entry is None:
        return discord.Embed(title="Nothing playing", color=discord.Color.greyple())
    embed = discord.Embed(title=entry.title, url=entry.webpage_url, color=discord.Color.blurple())
    state_label = "❚❚ Paused" if player.state == PlayerState.PAUSED else "▶ Playing"
    embed.add_field(name="State", value=state_label, inline=True)
    embed.add_field(name="Duration", value=_fmt_duration(entry.duration), inline=True)
    embed.add_field(name="Volume", value=f"{int(player.volume * 100)}%", inline=True)
    embed.add_field(name="Loop", value="On" if player.loop else "Off", inline=True)
    return embed


class PlayerView(discord.ui.View):
    def __init__(self, player: GuildPlayer) -> None:
        super().__init__(timeout=None)
        self.player = player
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        for child in self.children:
            if not isinstance(child, discord.ui.Button):
                continue
            if child.custom_id == "player_loop":
                child.style = discord.ButtonStyle.success if self.player.loop else discord.ButtonStyle.secondary
            elif child.custom_id == "player_pause_resume":
                child.label = "▶" if self.player.state == PlayerState.PAUSED else "⏸"

    # ── Row 0: playback ──────────────────────────────────────────────────────

    @discord.ui.button(label="⏸", style=discord.ButtonStyle.primary, custom_id="player_pause_resume", row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.player.state == PlayerState.PAUSED:
            self.player.resume()
        else:
            self.player.pause()
        self._sync_buttons()
        await interaction.response.edit_message(embed=build_embed(self.player), view=self)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.secondary, custom_id="player_skip", row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.player.skip()
        await interaction.response.defer()

    @discord.ui.button(label="↺", style=discord.ButtonStyle.secondary, custom_id="player_loop", row=0)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.player.toggle_loop()
        self._sync_buttons()
        await interaction.response.edit_message(embed=build_embed(self.player), view=self)

    @discord.ui.button(label="☰", style=discord.ButtonStyle.secondary, custom_id="player_queue", row=0)
    async def queue(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        lines: list[str] = []
        if self.player.current:
            lines.append(f"▶ **{self.player.current.title}**")
        for i, entry in enumerate(self.player.get_queue_snapshot(), start=1):
            lines.append(f"`{i}.` {entry.title}")
        content = "\n".join(lines) if lines else "Queue is empty."
        await interaction.response.send_message(content, ephemeral=True)

    # ── Row 1: utilities ─────────────────────────────────────────────────────

    @discord.ui.button(label="🔈", style=discord.ButtonStyle.secondary, custom_id="player_vol_down", row=1)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.player.set_volume(max(0.0, round(self.player.volume - 0.1, 2)))
        await interaction.response.edit_message(embed=build_embed(self.player), view=self)

    @discord.ui.button(label="🔊", style=discord.ButtonStyle.secondary, custom_id="player_vol_up", row=1)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.player.set_volume(min(2.0, round(self.player.volume + 0.1, 2)))
        await interaction.response.edit_message(embed=build_embed(self.player), view=self)

    @discord.ui.button(label="⏹", style=discord.ButtonStyle.danger, custom_id="player_clear", row=1)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.player.clear_queue()
        for child in self.children:
            child.disabled = True
        embed = discord.Embed(title="Queue cleared", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=self)
