# Wordle Solver

A local command-line assistant for the NYT daily Wordle. It knows today's answer, so it can
promise the puzzle is solved on attempt 3 or 4 — but it does not play for you. You tell it the
word you actually played, it prints the colours that word really drew, and it suggests the next
guess.

```
$ python -m wordle.play
Wordle · 2026-10-13 · solve in 4
consonant r · vowel e

1. suggestion  TERSE
   you played > TERSE
              ⬛🟨🟨⬛⬛

2. suggestion  AIDER
   you played > AIDER
              ⬛🟩🟩🟩🟩

3. suggestion  CIDER
   you played > CIDER
              ⬛🟩🟩🟩🟩

4. suggestion  WIDER   <- this is the answer
   you played > WIDER
              🟩🟩🟩🟩🟩

solved in 4
```

## Setup

Python 3.12+.

```
python -m venv .venv
source .venv/Activate.ps1        # Windows PowerShell
pip install -r requirements.txt  # tzdata, Windows only
```

Nothing else to configure. No token, no account, no server.

## Run

```
python -m wordle.play              # today's puzzle, solve in 4
python -m wordle.play 3            # solve in 3
python -m wordle.play 4 yodel      # use `yodel` as the answer instead of fetching
python -m wordle.nytimes           # just today's answer
```

In the loop: press **Enter** to take the suggestion, or type the five-letter word you played
instead. The candidate set follows what you actually played, so overriding a suggestion changes
the next one. A word that the colours already ruled out is still accepted — it is your move — with
a note saying so.

## How it decides

- **Guess 1** — the highest-scoring word from the official answer list that contains both letters
  NYT hints for.
- **Guesses 2..N-1** — the guess that best splits the words still consistent with the feedback so
  far, restricted to words that are themselves still possible answers. That constraint is what
  makes the sequence look like competent play rather than a machine emptying a dictionary.
- **Attempt N** — the answer. Always. Guessing the answer is a legal Wordle move, so the promise
  cannot fail.

The one exception: if the answer is the only word left that fits the colours before attempt N, the
tool stalls with a filler word instead of spoiling the attempt early, and says so in the note
line.

## Limits

- **The bundled answer list drifts.** Sampling 42 dates across 2024–2026, 5 of the 42 answers
  (`spate`, `tizzy`, `shill`, `soupy`, `pager`) are missing from `data/answers.txt`. It does not
  break the guarantee: today's answer is always added to the universe before guessing.
- **One request per day.** The answer is fetched from the NYT endpoint and cached in `cache.json`,
  so a day is fetched at most once. If the endpoint is down, pass the answer on the command line.
- **The date is pinned to New York time**, because that is when NYT rolls the puzzle. On Windows
  that needs the `tzdata` package; Linux and macOS already ship a tz database.
- **Emoji output** needs a UTF-8 console. `python -m wordle.play` reconfigures stdout itself; if
  you import the modules from your own script, you may not.
- Scraping the NYT answer is against the spirit of the game and arguably their terms. Personal
  use, one request a day.

## Tests

```
python -m unittest discover -s tests        # ~3 s, offline
WORDLE_REPLAY_ALL=1 python -m unittest discover -s tests   # ~90 s
```

The replay sweep plays all 2,315 answers for both attempt counts and asserts the guarantee: the
last guess is the answer, no guess repeats, and no guess is ever eliminated by the feedback it
itself drew. That is the same code path the CLI walks when you accept every suggestion.

## Not included

No Discord bot, webhook, or token — that existed and was removed; it is in git history. No
"honest" mode that solves without knowing the answer.
