"""Today's Wordle answer: NYT endpoint, on-disk store, manual override.

One file, `cache.json`, is the store. The endpoint fills it, `set_answer` overwrites an entry in
it, and reads consult it first — so a manual override survives every later fetch.
"""

import json
import re
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

_URL = "https://www.nytimes.com/svc/wordle/v2/{iso}.json"
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
_STORE_PATH = Path(__file__).resolve().parent.parent / "cache.json"
_EASTERN = ZoneInfo("America/New_York")


def today(now: datetime | None = None) -> date:
    """Puzzle date. NYT rolls at midnight Eastern, not UTC."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(_EASTERN).date()


def get_answer(day: date, store_path: Path = _STORE_PATH) -> str:
    stored = _read(store_path).get(day.isoformat())
    if stored:
        return stored
    answer = _validate(_fetch(day), source="NYT endpoint")
    store = _read(store_path)
    store[day.isoformat()] = answer
    _write(store_path, store)
    return answer


def set_answer(answer: str, day: date | None = None, store_path: Path = _STORE_PATH) -> str:
    answer = _validate(answer, source="override")
    store = _read(store_path)
    store[(day or today()).isoformat()] = answer
    _write(store_path, store)
    return answer


def _fetch(day: date) -> str:
    request = urllib.request.Request(_URL.format(iso=day.isoformat()), headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)["solution"]


def _validate(answer: str, source: str) -> str:
    answer = str(answer).lower()
    if not re.fullmatch(r"[a-z]{5}", answer):
        raise ValueError(f"{source} gave an unusable answer: {answer!r}")
    return answer


def _read(store_path: Path) -> dict[str, str]:
    try:
        return json.loads(store_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write(store_path: Path, store: dict[str, str]) -> None:
    store_path.write_text(json.dumps(store, indent=1, sort_keys=True), encoding="utf-8")
