"""The CLI loop: accepting a suggestion, overriding it, and the bridge to `sequence`."""

import contextlib
import io
import re
import unittest

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

    def test_an_eliminated_guess_is_accepted_with_a_note(self):
        _, out = run(["4", "range"], ["crane", "slate", "", ""])
        self.assertIn("already eliminated", out)
        self.assertEqual(suggestions(out)[-1], "RANGE")

    def test_a_stall_is_explained_rather_than_flagged(self):
        _, out = run(["4", "range"], ["", "", "", ""])
        self.assertIn("this guess is a stall", out)
        self.assertNotIn("already eliminated", out)


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


if __name__ == "__main__":
    unittest.main()
