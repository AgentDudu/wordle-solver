import re
import unittest
from datetime import date

from wordle import bot
from wordle.solver import render, sequence

GUESS_LINE = re.compile(r"^\d\. (?:\|\|)?[A-Z]{5}(?:\|\|)?  ")


def guess_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if GUESS_LINE.match(line)]


class PuzzleText(unittest.TestCase):
    def test_header_and_hints(self):
        lines = bot.puzzle_text(date(2026, 10, 13), 3, "wider").splitlines()
        self.assertIn("2026-10-13", lines[0])
        self.assertIn("solve in 3", lines[0])
        self.assertIn("consonant R", lines[1])
        self.assertIn("vowel E", lines[1])

    def test_answer_count_and_spoiler(self):
        text = bot.puzzle_text(date(2026, 10, 13), 3, "wider")
        self.assertEqual(len(guess_lines(text)), 3)
        self.assertIn("||WIDER||", text)

    def test_attempt_count_controls_the_guess_count(self):
        for attempts in (3, 4):
            with self.subTest(attempts=attempts):
                text = bot.puzzle_text(date(2026, 10, 13), attempts, "crane")
                self.assertEqual(len(guess_lines(text)), attempts)
                self.assertTrue(guess_lines(text)[-1].startswith(f"{attempts}. ||"))

    def test_answer_without_a_vowel_omits_that_hint(self):
        lines = bot.puzzle_text(date(2026, 10, 13), 4, "crypt").splitlines()
        self.assertIn("consonant T", lines[1])
        self.assertNotIn("vowel", lines[1])

    def test_console_render_has_no_spoiler(self):
        rendered = render(sequence("wider", 3))
        self.assertIn("WIDER", rendered)
        self.assertNotIn("||WIDER||", rendered)


class CommandTree(unittest.TestCase):
    def test_the_three_commands_register(self):
        # Catches slash-command API misuse (bad decorators, bad annotations) without a token.
        client = bot.WordleClient()
        client.tree.add_command(bot._WORDLE)
        [group] = client.tree.get_commands()
        self.assertEqual(group.name, "wordle")
        self.assertEqual(sorted(sub.name for sub in group.commands), ["answer", "setanswer", "solve"])


if __name__ == "__main__":
    unittest.main()
