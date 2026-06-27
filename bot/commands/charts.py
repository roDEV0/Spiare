import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates
from matplotlib import font_manager
import numpy as np
import discord
import discord.ext.commands as commands
from discord import app_commands
from typing import Literal
import datetime
import tempfile
import os
import skinpy

from shared.database import Players, Sessions, Towns, PlayerSnapshot, TownSnapshot

metric_mapping = {
    "Gold": "gold",
    "Town Blocks": "town_blocks",
    "Population": "total_citizens",
    "Sessions": "total_sessions",
}


class Charts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        font_manager.fontManager.addfont("shared/assets/determination.ttf")
        prop = font_manager.FontProperties(fname="shared/assets/determination.ttf")

        plt.rcParams["font.family"] = prop.get_name()
        plt.rcParams["timezone"] = "UTC"

        plt.style.use("dark_background")

    chart_group = app_commands.Group(
        name="chart", description="Chart snapshot information"
    )

    def _create_plot(self, snapshots, metric, subject):
        fig, ax = plt.subplots(dpi=300)
        ax.set_title(f"{subject} {metric} Over Time")
        ax.set_xlabel("Time (M-D H)")
        ax.set_ylabel(metric)

        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.AutoDateFormatter(locator))
        fig.autofmt_xdate()
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))

        start_dict = snapshots[0].__dict__
        end_dict = snapshots[-1].__dict__

        average_dates = [start_dict["date"], end_dict["date"]]
        average_values = [
            start_dict[metric_mapping[metric]],
            end_dict[metric_mapping[metric]],
        ]
        if metric == "Town Blocks":
            average_values = [
                len(start_dict["town_blocks"]),
                len(end_dict["town_blocks"]),
            ]

        dates = []
        values = []

        for snapshot in snapshots:
            entry_dict = snapshot.__dict__
            dates.append(entry_dict["date"])
            if metric == "Town Blocks":
                print(len(entry_dict["town_blocks"]))
                values.append(len(entry_dict["town_blocks"]))
            else:
                values.append(entry_dict[metric_mapping[metric]])

        ax.plot(dates, values, label="Actual")
        ax.plot(average_dates, average_values, label="Average")

        ax.legend()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        fig.savefig(tmp_path, bbox_inches="tight", dpi=300)

        return tmp_path

    def _create_embed(self, town, metric, snapshots):
        start_dict = snapshots[0].__dict__
        end_dict = snapshots[-1].__dict__

        if metric == "Town Blocks":
            difference = len(end_dict[metric_mapping[metric]]) - len(
                start_dict[metric_mapping[metric]]
            )
        else:
            difference = (
                end_dict[metric_mapping[metric]] - start_dict[metric_mapping[metric]]
            )

        start_value = (
            start_dict[metric_mapping[metric]]
            if metric != "Town Blocks"
            else len(start_dict[metric_mapping[metric]])
        )
        end_value = (
            end_dict[metric_mapping[metric]]
            if metric != "Town Blocks"
            else len(end_dict[metric_mapping[metric]])
        )

        embed = discord.Embed(
            title=f"{town} {metric} data",
            color=discord.Color.from_rgb(80, 54, 138),
        )

        embed.set_author(name=town)
        embed.add_field(
            name="Timeframe Start",
            value=f"<t:{int(snapshots[-1].date.timestamp())}:F>",
            inline=False,
        )
        embed.add_field(name="Days", value=f"{len(snapshots)}", inline=True)
        embed.add_field(name="Start", value=f"{start_value}", inline=True)
        embed.add_field(name="End", value=f"{end_value}", inline=True)
        embed.add_field(
            name="Growth",
            value=f"```diff\n{"+" if difference >= 0 else "-"} {abs(difference)}\n```",
            inline=True,
        )
        embed.add_field(
            name="Rate",
            value=f"```diff\n{"+" if difference >= 0 else "-"} {abs(difference / len(snapshots)):.2f}/Day\n```",
            inline=True,
        )
        embed.set_image(url="attachment://chart.png")

        return embed

    @chart_group.command(name="town", description="Chart town data over time")
    async def town_chart(
        self,
        interaction: discord.Interaction,
        town: str,
        metric: Literal["Gold", "Town Blocks", "Population"],
        days: int,
    ):
        await interaction.response.defer()

        timeframe = datetime.timedelta(days=days)

        town_obj = await Towns.get_or_none(name=town)
        if not town_obj:
            await interaction.followup.send(
                f"The town **{town}** has not had any snapshots"
            )
            return

        relevant_snapshots = await TownSnapshot.filter(
            town=town_obj.id, date__gte=datetime.datetime.now() - timeframe
        ).order_by("date")

        tmp_path = self._create_plot(relevant_snapshots, metric, town)
        embed = self._create_embed(town, metric, relevant_snapshots)

        image_file = discord.File(tmp_path, filename="chart.png")
        await interaction.followup.send(embed=embed, file=image_file)

        os.remove(tmp_path)

    @chart_group.command(name="player", description="Chart player data over time")
    async def player_chart(
        self,
        interaction: discord.Interaction,
        player: str,
        metric: Literal["Gold", "Sessions"],
        days: int,
    ):
        await interaction.response.defer()

        timeframe = datetime.timedelta(days=days)

        player_obj = await Players.get_or_none(username=player)
        if not player_obj:
            await interaction.followup.send(
                f"The player **{player}** has not had any snapshots"
            )
            return

        relevant_snapshots = await PlayerSnapshot.filter(
            player=player_obj.id, date__gte=datetime.datetime.now() - timeframe
        ).order_by("date")

        tmp_path = self._create_plot(relevant_snapshots, metric, player)
        embed = self._create_embed(player, metric, relevant_snapshots)

        image_file = discord.File(tmp_path, filename="chart.png")
        await interaction.followup.send(embed=embed, file=image_file)

        os.remove(tmp_path)
