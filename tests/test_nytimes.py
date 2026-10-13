import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from wordle import nytimes

NYT_RESPONSE = b'{"id":2024,"solution":"quail","print_date":"2025-06-15","days_since_launch":1457}'


class _Response:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Endpoint(unittest.TestCase):
    def test_reads_the_solution_field(self):
        with patch.object(nytimes.urllib.request, "urlopen", return_value=_Response(NYT_RESPONSE)):
            self.assertEqual(nytimes._fetch(date(2025, 6, 15)), "quail")

    def test_rejects_an_unusable_endpoint_answer(self):
        with patch.object(nytimes, "_fetch", return_value="not a word"):
            with self.assertRaises(ValueError):
                nytimes.get_answer(date(2025, 6, 15), _store(self))


class Store(unittest.TestCase):
    def setUp(self):
        self.path = _store(self)
        self.day = date(2025, 6, 15)

    def test_fetches_once_then_serves_from_the_store(self):
        with patch.object(nytimes, "_fetch", return_value="QUAIL") as fetch:
            self.assertEqual(nytimes.get_answer(self.day, self.path), "quail")
            self.assertEqual(nytimes.get_answer(self.day, self.path), "quail")
        self.assertEqual(fetch.call_count, 1)

    def test_override_survives_later_fetches(self):
        nytimes.set_answer("yodel", self.day, self.path)
        with patch.object(nytimes, "_fetch", side_effect=AssertionError("must not fetch")):
            self.assertEqual(nytimes.get_answer(self.day, self.path), "yodel")

    def test_override_rejects_bad_words(self):
        for bad in ("yodels", "yode", "y0del", "yodel ", ""):
            with self.assertRaises(ValueError):
                nytimes.set_answer(bad, self.day, self.path)

    def test_corrupt_store_falls_back_to_the_endpoint(self):
        self.path.write_text("not json", encoding="utf-8")
        with patch.object(nytimes, "_fetch", return_value="quail"):
            self.assertEqual(nytimes.get_answer(self.day, self.path), "quail")


class PuzzleDate(unittest.TestCase):
    def test_rolls_at_midnight_eastern(self):
        just_before = datetime(2025, 6, 15, 3, 0, tzinfo=timezone.utc)  # 23:00 EDT on the 14th
        just_after = datetime(2025, 6, 15, 4, 30, tzinfo=timezone.utc)  # 00:30 EDT on the 15th
        self.assertEqual(nytimes.today(just_before), date(2025, 6, 14))
        self.assertEqual(nytimes.today(just_after), date(2025, 6, 15))


def _store(case: unittest.TestCase) -> Path:
    tmp = tempfile.TemporaryDirectory()
    case.addCleanup(tmp.cleanup)
    return Path(tmp.name) / "cache.json"


if __name__ == "__main__":
    unittest.main()
