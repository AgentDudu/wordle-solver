"""The entry point: flag parsing, the `answer` subcommand, and what reaches the session."""

import contextlib
import io
import unittest
from datetime import date
from unittest.mock import patch

import main as cli
from wordle import nytimes, play


def run(argv):
    """Run the CLI; return (exit code, everything printed).

    stdout and stderr share one buffer because argparse reports a refused argument on stderr while
    the session itself writes to stdout, and both are asserted here. A refused argument ends in
    SystemExit(2) rather than a return value, so that is captured as the code too.
    """
    text = io.StringIO()
    try:
        with contextlib.redirect_stdout(text), contextlib.redirect_stderr(text):
            code = cli.main(argv)
    except SystemExit as refused:
        code = refused.code
    return code, text.getvalue()


class FlagPlumbing(unittest.TestCase):
    def test_the_flags_reach_the_session(self):
        with patch.object(play, "main", return_value=0) as session:
            code, _ = run(["-n", "3", "-a", "RANGE"])
        self.assertEqual(code, 0)
        self.assertEqual(session.call_args.kwargs, {"attempts": 3, "answer": "range"})

    def test_nothing_is_assumed_about_the_defaults(self):
        # Both stay None so the session asks for the attempt count and fetches today's answer.
        with patch.object(play, "main", return_value=0) as session:
            code, _ = run([])
        self.assertEqual(code, 0)
        self.assertEqual(session.call_args.kwargs, {"attempts": None, "answer": None})

    def test_the_long_flags_work_too(self):
        with patch.object(play, "main", return_value=0) as session:
            run(["--attempts", "4", "--answer", "yodel"])
        self.assertEqual(session.call_args.kwargs, {"attempts": 4, "answer": "yodel"})

    def test_an_answer_that_is_not_five_letters_is_refused_before_the_session(self):
        for value in ("ranged", "yodl", "yod3r"):
            with patch.object(play, "main", return_value=0) as session:
                code, out = run(["-a", value])
            self.assertEqual(code, 2, value)
            self.assertIn("is not five letters a-z", out)
            session.assert_not_called()

    def test_an_attempt_count_outside_three_and_four_is_refused(self):
        for value in ("5", "2", "zero"):
            with patch.object(play, "main", return_value=0) as session:
                code, _ = run(["-n", value])
            self.assertEqual(code, 2, value)
            session.assert_not_called()

    def test_the_old_positional_form_is_refused_rather_than_misread(self):
        with patch.object(play, "main", return_value=0) as session:
            code, out = run(["4", "yodel"])
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", out)
        session.assert_not_called()

    def test_help_names_both_commands_and_both_flags(self):
        code, out = run(["--help"])
        self.assertEqual(code, 0)
        for text in ("{play,answer}", "--attempts", "--answer"):
            self.assertIn(text, out)

    def test_a_failed_fetch_names_the_flag_that_replaces_it(self):
        with patch.multiple(nytimes, today=lambda: date(2026, 10, 13), get_answer=_refuse):
            code, out = run([])
        self.assertEqual(code, 1)
        self.assertIn("could not get today's answer", out)
        self.assertIn("python main.py --answer <answer>", out)


class AnswerSubcommand(unittest.TestCase):
    def setUp(self):
        self.today = patch.object(nytimes, "today", lambda: date(2026, 10, 13))
        self.today.start()
        self.addCleanup(self.today.stop)

    def test_it_prints_the_date_answer_and_where_it_came_from(self):
        for source in ("cache", "NYT endpoint"):
            with patch.object(nytimes, "lookup", return_value=("wider", source)):
                code, out = run(["answer"])
            self.assertEqual(code, 0)
            self.assertIn(f"2026-10-13  wider  ({source})", out)

    def test_a_given_answer_skips_the_endpoint_entirely(self):
        with patch.object(nytimes, "lookup", side_effect=AssertionError("must not look up")):
            code, out = run(["answer", "-a", "yodel"])
        self.assertEqual(code, 0)
        self.assertIn("2026-10-13  yodel  (given on the command line)", out)

    def test_an_unreachable_endpoint_exits_1_without_a_traceback(self):
        with patch.object(nytimes, "lookup", _refuse):
            code, out = run(["answer"])
        self.assertEqual(code, 1)
        self.assertIn("could not get today's answer: endpoint down", out)
        self.assertIn("python main.py answer --answer <answer>", out)
        self.assertNotIn("Traceback", out)


def _refuse(*args, **kwargs):
    raise OSError("endpoint down")


if __name__ == "__main__":
    unittest.main()
