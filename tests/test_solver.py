import os
import unittest

from wordle.solver import Game, colorize, hints, load_answers, sequence

# Real NYT answers that data/answers.txt does not contain; see SPEC.md 3.3.
OUT_OF_LIST = ["yodel", "aspic"]

# Full replay costs minutes; the structural guarantees below do not depend on scoring quality,
# so the default run samples the list and WORDLE_REPLAY_ALL=1 sweeps all 2,315 answers.
STRIDE = 100


class Colorize(unittest.TestCase):
    def test_all_green(self):
        self.assertEqual(colorize("crane", "crane"), (2, 2, 2, 2, 2))

    def test_repeated_guess_letter_matches_only_available_answer_letters(self):
        self.assertEqual(colorize("speed", "abide"), (0, 0, 1, 0, 1))

    def test_green_consumes_letter_before_yellow(self):
        self.assertEqual(colorize("aaabb", "baaab"), (1, 2, 2, 1, 2))

    def test_no_feedback(self):
        self.assertEqual(colorize("crane", "lymph"), (0, 0, 0, 0, 0))


class Sequence(unittest.TestCase):
    def setUp(self):
        self.answers = load_answers()

    def test_sampled_replay(self):
        for answer in self.answers[::STRIDE]:
            self._check(answer)

    def test_answers_missing_from_the_list(self):
        for answer in OUT_OF_LIST:
            self._check(answer)

    def test_full_replay(self):
        if not os.environ.get("WORDLE_REPLAY_ALL"):
            self.skipTest("set WORDLE_REPLAY_ALL=1 to sweep every answer")
        for answer in self.answers:
            self._check(answer)

    def test_rejects_other_attempt_counts(self):
        for bad in (0, 1, 2, 5, 6):
            with self.assertRaises(ValueError):
                sequence("crane", bad)

    def test_the_answer_is_normalised_to_lowercase(self):
        self.assertEqual(Game("RANGE", 4).answer, "range")
        self.assertEqual(sequence("RANGE", 4)[-1][0], "range")

    def _check(self, answer):
        for attempts in (3, 4):
            seq = sequence(answer, attempts)
            with self.subTest(answer=answer, attempts=attempts):
                self.assertEqual(len(seq), attempts)
                self.assertEqual(seq[-1][0], answer)
                self.assertEqual(seq[-1][1], (2, 2, 2, 2, 2))
                self.assertEqual(len({w for w, _ in seq}), attempts)

                consonant, vowel = hints(answer)
                opener = seq[0][0]
                if consonant:
                    self.assertIn(consonant, opener)
                if vowel:
                    self.assertIn(vowel, opener)

                # Simulate a player who only ever sees feedback: every guess must be a word
                # still live in that player's head, and the answer must never be eliminated.
                live = set(self.answers) | {answer}
                for index, (word, colors) in enumerate(seq):
                    self.assertEqual(colors, colorize(word, answer))
                    if word not in live:
                        # Documented exception: the answer is the only consistent word left,
                        # so a filler is guessed rather than spoiling the attempt early.
                        self.assertEqual(live, {answer}, f"guess {index + 1} is not live")
                    live &= {c for c in live if colorize(word, c) == colors}
                    self.assertIn(answer, live)


if __name__ == "__main__":
    unittest.main()
