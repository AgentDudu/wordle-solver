import re
import unittest
from pathlib import Path

ANSWERS = Path(__file__).resolve().parent.parent / "data" / "answers.txt"


class AnswerList(unittest.TestCase):
    def setUp(self):
        self.words = ANSWERS.read_text(encoding="utf-8").split()

    def test_words_are_five_lowercase_letters(self):
        bad = [w for w in self.words if not re.fullmatch(r"[a-z]{5}", w)]
        self.assertEqual(bad, [])

    def test_no_duplicates(self):
        self.assertEqual(len(self.words), len(set(self.words)))

    def test_expected_size(self):
        # Official NYT answer list snapshot; see SPEC.md 3.3 for the staleness caveat.
        self.assertEqual(len(self.words), 2315)


if __name__ == "__main__":
    unittest.main()
