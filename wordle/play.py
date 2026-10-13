"""Interactive CLI: suggest a guess, take the word the player actually played.

The colours are computed here rather than typed in, because the answer is already known, so a
mis-entered pattern cannot poison the candidate set.
"""

import re
import sys

from . import nytimes
from .solver import FEEDBACK, Game, hints

_USAGE = "usage: python -m wordle.play [3|4] [answer]"


def main(argv: list[str] | None = None, read=input) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    n, answer = 4, None
    try:
        if argv:
            n = int(argv[0])
        if len(argv) > 1:
            answer = argv[1]
        if len(argv) > 2 or n not in (3, 4) or (answer and not re.fullmatch(r"[a-z]{5}", answer)):
            raise ValueError
    except ValueError:
        print(_USAGE)
        return 2

    day = None
    if answer is None:
        try:
            day = nytimes.today()
            answer = nytimes.get_answer(day)
        except Exception as exc:  # URLError, HTTPError, bad JSON, unusable solution
            print(f"could not get today's answer: {exc}")
            print(f"pass it directly: python -m wordle.play {n} <answer>")
            return 1

    game = Game(answer, n)
    consonant, vowel = hints(answer)
    print(f"Wordle · {day.isoformat() if day else 'answer given on the command line'} · solve in {n}")
    print(f"consonant {consonant} · vowel {vowel or 'none'}")

    while True:
        attempt = len(game.played) + 1
        guess = game.suggestion()
        note = "   <- this is the answer" if guess == answer else ""
        print(f"\n{attempt}. suggestion  {guess.upper()}{note}")
        try:
            typed = read("   you played > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(f"\nstopped after {len(game.played)} attempt(s); the answer was {answer.upper()}")
            return 1
        entry = typed or guess
        if not re.fullmatch(r"[a-z]{5}", entry):
            print("   five letters a-z, or press Enter to take the suggestion")
            continue

        live = entry in game.survivors
        # Only the answer fits the colours, so the suggestion is a deliberate stall rather than a
        # candidate — the one documented exception to the consistency rule.
        stall = guess != answer and game.survivors == [answer]
        colors = game.play(entry)
        print("              " + "".join(FEEDBACK[c] for c in colors))
        if typed and not live:
            print("   note: that word was already eliminated by the colours above")
        elif stall:
            print("   note: only the answer fits the colours, so this guess is a stall")
        if game.solved:
            print(f"\nsolved in {attempt}")
            return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252, no emoji
    raise SystemExit(main())
