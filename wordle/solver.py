"""Guess generation for a Wordle puzzle whose answer is already known."""

import math
from collections import Counter
from pathlib import Path

GREEN, YELLOW, GRAY = 2, 1, 0

# English letter frequency, most common first. Used to pick which hinted letters to reveal.
_FREQ = "etaoinshrdlcumwfgypbvkjxqz"
_VOWELS = frozenset("aeiou")
_ANSWERS_PATH = Path(__file__).resolve().parent.parent / "data" / "answers.txt"

_FEEDBACK = {GREEN: "🟩", YELLOW: "🟨", GRAY: "⬛"}


def load_answers(path: Path = _ANSWERS_PATH) -> list[str]:
    return sorted(path.read_text(encoding="utf-8").split())


def colorize(guess: str, answer: str) -> tuple[int, int, int, int, int]:
    """Wordle feedback for `guess` against `answer`: greens first, then yellows
    against still-unmatched answer letters, so repeated letters score correctly."""
    colors = [GRAY] * 5
    unmatched = []
    for i, (g, a) in enumerate(zip(guess, answer)):
        if g == a:
            colors[i] = GREEN
        else:
            unmatched.append(a)
    for i, g in enumerate(guess):
        if colors[i] == GRAY and g in unmatched:
            colors[i] = YELLOW
            unmatched.remove(g)
    return tuple(colors)


def hints(answer: str) -> tuple[str | None, str | None]:
    """(consonant, vowel) present in `answer`, the most frequent of each.

    Returns vowel None for the 13 answers with no aeiou letter (crypt, gypsy, ...);
    NYT's own hint behaviour for those is not reproduced.
    """
    present = sorted(set(answer), key=_FREQ.index)
    consonant = next((c for c in present if c not in _VOWELS), None)
    vowel = next((c for c in present if c in _VOWELS), None)
    return consonant, vowel


def score(word: str, pool: list[str]) -> float:
    """Shannon entropy (bits) of the partition `pool` falls into when scored against `word`."""
    n = len(pool)
    if n < 2:
        return 0.0
    counts = Counter(colorize(word, candidate) for candidate in pool)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def sequence(answer: str, n: int, answers: list[str] | None = None) -> list[tuple[str, tuple[int, ...]]]:
    """`n` guesses ending with `answer`. Every guess before the last is consistent with
    the answer's real feedback, so the colours printed here are the colours NYT will show."""
    if n not in (3, 4):
        raise ValueError("solve attempt must be 3 or 4")

    universe = sorted(set(load_answers() if answers is None else answers) | {answer})
    consonant, vowel = hints(answer)
    hinted = [
        w
        for w in universe
        if (consonant is None or consonant in w) and (vowel is None or vowel in w)
    ]
    pool = hinted or universe  # shortcut: hint constraint dropped when no universe word satisfies it

    candidates = [w for w in pool if w != answer]
    opener = max(candidates, key=lambda w: score(w, pool))
    guesses = [opener]
    # A word stays eligible only while it is still a possible answer given the feedback seen so
    # far: colorize(guess, word) must equal the feedback that guess actually drew. The tracking
    # spans the whole universe, not just the hint-filtered pool, because a later guess may
    # legitimately sit outside the hint filter.
    survivors = [w for w in universe if colorize(opener, w) == colorize(opener, answer)]

    for _ in range(2, n):
        # The answer itself is never guessed early; if it is the only consistent word left,
        # fall back to a filler from the universe rather than spoiling the attempt.
        choices = [w for w in survivors if w not in guesses and w != answer]
        if not choices:
            choices = [w for w in universe if w not in guesses and w != answer]
        guess = max(choices, key=lambda w: score(w, survivors))
        guesses.append(guess)
        survivors = [w for w in survivors if colorize(guess, w) == colorize(guess, answer)]

    guesses.append(answer)
    return [(word, colorize(word, answer)) for word in guesses]


def render(seq: list[tuple[str, tuple[int, ...]]]) -> str:
    return "\n".join(
        f"{i}. {word.upper()}  {''.join(_FEEDBACK[c] for c in colors)}"
        for i, (word, colors) in enumerate(seq, 1)
    )


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252, no emoji
    word = sys.argv[1] if len(sys.argv) > 1 else "crane"
    attempts = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    consonant, vowel = hints(word)
    print(f"hints: consonant {consonant} · vowel {vowel}")
    print(render(sequence(word, attempts)))
