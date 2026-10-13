"""Today's Wordle answer: NYT endpoint plus an on-disk cache, one entry per day.

`cache.json` holds the fetched answers. Reads consult it first, so a day is fetched at most once.
"""

import json
import re
import urllib.request
from datetime import date, datetime
from pathlib import Path

_URL = "https://www.nytimes.com/svc/wordle/v2/{iso}.json"
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
_STORE_PATH = Path(__file__).resolve().parent.parent / "cache.json"


def today(now: datetime | None = None) -> date:
    """Puzzle date: the player's own local date.

    NYT resets at local midnight for each player, and the endpoint answers for any date you ask
    it for — `2026-10-14.json` served `psych` with `days_since_launch: 1943` while New York was
    still on the 13th. Pinning this to Eastern handed UTC+8 players yesterday's puzzle.
    """
    return (now or datetime.now()).astimezone().date()


def get_answer(day: date, store_path: Path = _STORE_PATH) -> str:
    stored = _read(store_path).get(day.isoformat())
    if stored:
        return stored
    answer = _validate(_fetch(day), source="NYT endpoint")
    store = _read(store_path)
    store[day.isoformat()] = answer
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


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    day = today()
    cached = _read(_STORE_PATH).get(day.isoformat())
    print(f"{day.isoformat()}  {cached or get_answer(day)}  ({'cache' if cached else 'NYT endpoint'})")
