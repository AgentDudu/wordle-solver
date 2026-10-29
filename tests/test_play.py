"""The CLI loop: accepting a suggestion, overriding it, and the bridge to `sequence`."""

import contextlib
import io
import re
import unittest
from datetime import date
from unittest.mock import patch

from wordle import play, solver


def run(argv, words):
    """Run one session with scripted input; return (exit code, transcript)."""
    spoken = iter(words)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = play.main(argv, read=lambda prompt="": next(spoken, ""))
    return code, out.getvalue()


def suggestions(transcript):
    return [w for _, w in re.findall(r"^(\d)\. suggestion  (\w+)", transcript, re.M)]


def todays_puzzle(answer):
    """Serve a fixed answer for today's date, so a run with no answer argument stays offline.

    The `read` stub below swallows the prompt text, so these tests assert the session header
    (`solve in N`) rather than the question itself.
    """
    return patch.multiple(
        play.nytimes, today=lambda: date(2026, 10, 13), get_answer=lambda day: answer
    )


class AcceptingSuggestions(unittest.TestCase):
    def test_the_cli_path_is_the_proven_sequence(self):
        for answer in ("crane", "range", "spate", "crypt"):
            for n in (3, 4):
                code, out = run([str(n), answer], [""] * 6)
                self.assertIn(f"answer  {answer.upper()}", out)
                self.assertEqual(
                    suggestions(out), [w.upper() for w, _ in solver.sequence(answer, n)]
                )
                self.assertEqual(code, 0)
                self.assertIn(f"solved in {n}", out)


class OverridingASuggestion(unittest.TestCase):
    def test_the_answer_still_lands_on_attempt_n(self):
        code, out = run(["4", "range"], ["crane", "", "", ""])
        self.assertEqual(suggestions(out)[-1], "RANGE")
        self.assertEqual(code, 0)
        self.assertIn("solved in 4", out)

    def test_the_colours_are_the_real_ones(self):
        _, out = run(["4", "range"], ["crane", "", "", ""])
        self.assertIn("⬛🟨🟨🟨🟩", out)

    def test_the_next_suggestion_follows_what_was_played(self):
        _, out = run(["4", "range"], ["crane", "", "", ""])
        third = suggestions(out)[2]
        colors = solver.colorize(third.lower(), "range")
        self.assertEqual(solver.colorize("crane", "range"), (0, 1, 1, 1, 2))
        self.assertNotEqual(colors, (2, 2, 2, 2, 2))

    def test_a_guess_off_the_answer_list_is_adapted_to_without_a_note(self):
        # `adieu` is a legal Wordle guess that data/answers.txt does not contain. The candidate
        # set must still narrow by its colours, and the word must not be called eliminated.
        _, out = run(["4", "range"], ["adieu", "", "", ""])
        self.assertNotIn("already eliminated", out)
        self.assertIn("🟨⬛⬛🟨⬛", out)
        self.assertEqual(suggestions(out)[-1], "RANGE")
        for word in (w.lower() for w in suggestions(out)[1:]):
            self.assertEqual(solver.colorize("adieu", word), solver.colorize("adieu", "range"))

    def test_overriding_the_early_suggestions_still_narrows_to_the_answer(self):
        # Every suggestion must fit the colours drawn by the guesses before it, including guesses
        # the solver never suggested. A suggestion at index i is shown on attempt i+1, so it is
        # only bound by the guesses of attempts 1..i.
        typed = ["adieu", "bingo"]
        _, out = run(["4", "range"], typed + ["", ""])
        self.assertEqual(suggestions(out)[-1], "RANGE")
        for attempt, word in enumerate(typed, 1):
            for later in (w.lower() for w in suggestions(out)[attempt:]):
                self.assertEqual(solver.colorize(word, later), solver.colorize(word, "range"))

    def test_an_eliminated_guess_is_accepted_with_a_note(self):
        _, out = run(["4", "range"], ["crane", "slate", "", ""])
        self.assertIn("already eliminated", out)
        self.assertEqual(suggestions(out)[-1], "RANGE")

    def test_a_stall_is_explained_rather_than_flagged(self):
        _, out = run(["4", "range"], ["", "", "", ""])
        self.assertIn("this guess is a stall", out)
        self.assertNotIn("already eliminated", out)


class AttemptCountPrompt(unittest.TestCase):
    def test_it_asks_how_many_attempts_when_none_was_given(self):
        with todays_puzzle("range"):
            code, out = run([], ["3", "", "", ""])
        self.assertEqual(code, 0)
        self.assertIn("solve in 3", out)
        self.assertIn("solved in 3", out)
        self.assertEqual(len(suggestions(out)), 3)

    def test_enter_at_the_prompt_keeps_the_default_of_four(self):
        with todays_puzzle("range"):
            code, out = run([], ["", "", "", "", ""])
        self.assertEqual(code, 0)
        self.assertIn("solved in 4", out)

    def test_an_answer_outside_three_or_four_repeats_without_consuming_a_guess(self):
        with todays_puzzle("range"):
            _, out = run([], ["2", "five", "4", "", "", "", ""])
        self.assertEqual(out.count("3 or 4, or press Enter for 4"), 2)
        self.assertIn("solve in 4", out)
        self.assertEqual(out.count("1. suggestion"), 1)

    def test_end_of_input_at_the_prompt_takes_the_default(self):
        def eof(prompt=""):
            raise EOFError

        out = io.StringIO()
        with todays_puzzle("range"), contextlib.redirect_stdout(out):
            code = play.main([], read=eof)
        self.assertEqual(code, 1)
        self.assertIn("solve in 4", out.getvalue())
        self.assertIn("the answer was RANGE", out.getvalue())

    def test_an_explicit_attempt_count_does_not_ask(self):
        # Three guesses offered for a three-attempt puzzle: if the prompt appeared it would eat
        # one of them and the run would stop short of the answer.
        code, out = run(["3", "range"], ["", "", ""])
        self.assertEqual(code, 0)
        self.assertIn("solved in 3", out)
        self.assertNotIn("press Enter", out)


class InputHandling(unittest.TestCase):
    def test_bad_input_does_not_consume_an_attempt(self):
        _, out = run(["4", "range"], ["nope!", "", "", ""])
        self.assertEqual(out.count("1. suggestion"), 2)
        self.assertIn("five letters a-z", out)

    def test_end_of_input_stops_and_shows_the_answer(self):
        def stop(prompt=""):
            raise EOFError

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = play.main(["4", "range"], read=stop)
        self.assertEqual(code, 1)
        self.assertIn("the answer was RANGE", out.getvalue())

    def test_attempt_count_outside_three_or_four_is_rejected(self):
        code, out = run(["5", "range"], [])
        self.assertEqual((code, out), (2, "usage: python -m wordle.play [3|4] [answer]\n"))

    def test_an_unusable_answer_is_rejected(self):
        self.assertEqual(run(["4", "ranged"], [])[0], 2)

    def test_an_uppercase_answer_argument_is_accepted(self):
        code, out = run(["4", "RANGE"], [""] * 6)
        self.assertEqual(code, 0)
        self.assertIn("answer  RANGE", out)
        self.assertIn("solved in 4", out)

    def test_typed_guesses_are_case_insensitive(self):
        code, out = run(["4", "range"], ["RaNgE"])
        self.assertEqual(code, 0)
        self.assertIn("solved in 1", out)


if __name__ == "__main__":
    unittest.main()
