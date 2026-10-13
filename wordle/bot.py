"""Discord interface: /wordle solve, /wordle answer, /wordle setanswer."""

import os
import sys
from datetime import date

import discord
from discord import app_commands

from . import nytimes
from .solver import hints, render, sequence

_WORDLE = app_commands.Group(name="wordle", description="NYT Wordle of the day")


def puzzle_text(day: date, attempts: int, answer: str) -> str:
    consonant, vowel = hints(answer)
    hint_line = " · ".join(
        f"{kind} {letter.upper()}"
        for kind, letter in (("consonant", consonant), ("vowel", vowel))
        if letter
    )
    header = f"Wordle · {day.isoformat()} · solve in {attempts}"
    return f"{header}\n{hint_line}\n\n{render(sequence(answer, attempts), spoiler_last=True)}"


def _unavailable(day: date, error: Exception) -> str:
    return (
        f"No answer for {day.isoformat()} ({error}). "
        f"Enter it with `/wordle setanswer <word>`."
    )


@_WORDLE.command(name="solve", description="Guesses, with the answer landing on the chosen attempt")
@app_commands.describe(attempt="Attempt the answer is guessed on")
async def solve(
    interaction: discord.Interaction, attempt: app_commands.Range[int, 3, 4]
) -> None:
    day = nytimes.today()
    try:
        answer = nytimes.get_answer(day)
    except Exception as error:  # endpoint down, bad payload: the user needs the override hint
        await interaction.response.send_message(_unavailable(day, error), ephemeral=True)
        return
    await interaction.response.send_message(
        embed=discord.Embed(description=puzzle_text(day, attempt, answer))
    )


@_WORDLE.command(name="answer", description="Today's answer, spoiler-wrapped and only for you")
async def answer(interaction: discord.Interaction) -> None:
    day = nytimes.today()
    try:
        word = nytimes.get_answer(day)
    except Exception as error:
        await interaction.response.send_message(_unavailable(day, error), ephemeral=True)
        return
    await interaction.response.send_message(f"||{word.upper()}||", ephemeral=True)


@_WORDLE.command(name="setanswer", description="Override today's answer")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(word="Five-letter answer")
async def setanswer(interaction: discord.Interaction, word: str) -> None:
    try:
        stored = nytimes.set_answer(word)
    except ValueError as error:
        await interaction.response.send_message(str(error), ephemeral=True)
        return
    await interaction.response.send_message(f"Set today's answer to {stored.upper()}")


@_WORDLE.error
async def wordle_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Administrator required.", ephemeral=True)
    else:
        raise error


class WordleClient(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.none())
        # discord.py 2.7 only gives `commands.Bot` a tree; a plain Client has to build one.
        # Constructing it is enough to route interactions, and no prefix-command machinery is needed.
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        self.tree.add_command(_WORDLE)
        await self.tree.sync()

    async def on_ready(self) -> None:
        print(f"logged in as {self.user}", file=sys.stderr)


def main() -> None:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN is not set")
    WordleClient().run(token)


if __name__ == "__main__":
    main()
