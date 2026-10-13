# Discord Wordle Solver — Final Specification

Supersedes `BRIEFING.md`. Every open question in §5 of that brief is resolved below.

## 1. Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | Solver lane | **Oracle-guided.** Bot fetches the true answer and uses it for every guess, not only the last. |
| 2 | Guarantee | **Unconditional.** Answer is guessed on attempt N. No fallback path exists. |
| 3 | "Enough yellow/green" threshold | **Removed.** Meaningless once the answer is known. |
| 4 | "Solve by attempt N" | **Option A.** Attempt N *is* the answer. N ∈ {3, 4}. |
| 5 | Interaction | **Script mode, stateless.** Full sequence printed at once. No feedback input, no per-user state. |
| 6 | NYT data | **Answer API only.** Hints derived locally from the answer. Wordle Review page is never scraped. |
| 7 | Guess pool | **Official answer list only** (~2,315 words). Never the 14,855-word allowed-guess list. |
| 8 | Guess 1 | **Highest-scoring answer-list word containing both hinted letters.** Not random. |
| 9 | Guesses 2..N-1 | **Entropy score over the surviving candidate set**, restricted to feedback-consistent words. |
| 10 | Discord | **Slash commands**, Python 3.12 + discord.py 2.x, runs locally. |
| 11 | Spoilers | Answer line wrapped in `\|\|spoiler\|\|`. |

## 2. Why the guarantee is unconditional

Guessing the answer is always a legal Wordle move, so attempt N always succeeds. The only
non-trivial requirement is that guesses `1..N-1` look like competent play and never contradict
themselves. That is enforced by the consistency rule in §4, and the eligible set is provably
never empty because the answer is always a member of it.

Consequence: the brief's §3.4 fallback, §4.2 threshold, and §4.3 Option B are all deleted from
the design.

## 3. Data

### 3.1 Answer
1. In-memory / on-disk cache for the date (`cache.json`).
2. `GET https://www.nytimes.com/svc/wordle/v2/YYYY-MM-DD.json` → `.answer`.
   Sends a browser `User-Agent`; NYT returns 403 without one. One request per day.
3. Manual override command `/wordle setanswer <word>` (owner-only, see §6).

Date is resolved in `America/New_York` — NYT rolls the puzzle at midnight ET, not UTC.

### 3.2 Hints
Derived locally, never scraped. `C` = most frequent consonant present in the answer,
`V` = most frequent vowel present, frequency order `etaoin shrdlu`. Deterministic per answer.

These may differ from the letters NYT's own "Give me a consonant / a vowel" buttons reveal.
Both are true statements about the word. Accepted trade-off — it removes the brittle,
bot-protected HTML scrape described in BRIEFING §2.

### 3.3 Word lists
`data/answers.txt` — the official NYT answer list, one word per line, lowercase.
`shortcut: static snapshot, breaks when NYT adds new answers; refresh by re-downloading the list.`

## 4. Algorithm

`colorize(guess, answer)` is standard Wordle two-pass scoring: greens first, then yellows
against unmatched letters only, so duplicate letters are handled correctly.

```
score(word, pool) = entropy of the partition of `pool` by colorize(word, candidate)
                    for candidate in pool          # Shannon, base 2

sequence(answer, N):
    C, V   = hints(answer)
    pool   = [w in ANSWERS if C in w and V in w]
    if not pool: pool = ANSWERS          # shortcut: hint constraint dropped if unsatisfiable

    g1     = argmax score(w, pool) for w in pool
    cands  = [w in pool if colorize(g1, w) == colorize(g1, answer)]

    for k in 2 .. N-1:
        gk     = argmax score(w, cands) for w in cands, tie-break by list order
        cands  = [w in cands if colorize(gk, w) == colorize(gk, answer)]

    gN     = answer
    return [g1, ..., gN] with feedback colorize(gi, answer) for each i
```

Two properties the tests assert:

- **Consistency.** Every guess `gi` satisfies `colorize(gi, answer) == colorize(gi, g_{i-1} feedback)`,
  i.e. copying the guess into NYT produces exactly the colours the bot printed.
- **Convergence.** `gN == answer`, and `len(sequence) == N`.

Scoring pool is the surviving candidate set itself, not the whole word list. This is both
faster (≈150×150 comparisons instead of 2,315×2,315, so a sequence computes in well under a
second in pure Python) and more humanlike — humans guess from words they think are still possible.

Sequences are cached per `(date, N)` next to the answer, so repeat calls are instant.

## 5. Output

One embed per command:

```
Wordle · 2026-02-12 · solve in 4
Hints: consonant R · vowel A

1. TRACE   🟩⬛🟨⬛⬛
2. RAISE   🟩🟨⬛⬛🟩
3. ARISE   🟨🟩⬛🟨⬛
4. ||RANGE||  🟩🟩🟩🟩🟩
```

## 6. Commands

| Command | Behaviour |
|---|---|
| `/wordle solve n:3\|4` | Print the sequence. |
| `/wordle answer` | Print only the answer, spoiler-wrapped. |
| `/wordle setanswer word:<5 letters>` | Override today's answer. Restricted to the bot owner. |

No prefix commands, no Message Content intent.

## 7. Layout

```
wordle/
    __init__.py
    nytimes.py      # answer fetch + cache + override
    solver.py       # colorize, score, sequence
    bot.py          # discord.py slash commands
data/answers.txt
tests/test_solver.py
requirements.txt    # discord.py>=2.3   (stdlib urllib for the HTTP call)
```

`DISCORD_TOKEN` from environment.

## 8. Test

`tests/test_solver.py` replays **every** word in `data/answers.txt` for N = 3 and N = 4 and
asserts: sequence length is N, last guess is the answer, every guess is in the answer list,
every guess is feedback-consistent, guess 1 contains both hint letters whenever any answer-list
word does. This test *is* the guarantee, made executable.

## 9. Implementation phases

Each phase is independently verifiable and lands on its own branch/PR. Nothing moves to the next
phase until the current phase's gate passes.

| Phase | Branch | Deliverable | Gate |
|---|---|---|---|
| **P0 — scaffold** | `feature/repo-scaffold` | Package layout, `requirements.txt`, `data/answers.txt`, `.gitignore`, `DISCORD_TOKEN` env contract. | `pip install -r requirements.txt` and `pytest` collect cleanly; no solver code yet. |
| **P1 — solver core** | `feature/solver-core` | `solver.py`: `colorize`, `score`, `hints`, `sequence`. `tests/test_solver.py` full-answer-list replay. | Replay passes for N=3 and N=4 over every answer word. `colorize` unit tests cover duplicate letters. Runs offline. |
| **P2 — data layer** | `feature/nytimes-answer` | `nytimes.py`: answer fetch with browser UA, `cache.json`, `America/New_York` date, local hint derivation, sequence cache, manual override store. | Offline test against a fixture response; expired/missing-cache path returns the override; no network in CI. |
| **P3 — Discord** | `feature/discord-commands` | `bot.py`: `/wordle solve`, `/wordle answer`, `/wordle setanswer`, embed renderer. | Bot runs locally against a real server; all three commands render; `setanswer` rejected for non-owners. |
| **P4 — hardening** | `feature/error-handling` | NYT failure → cache → override chain surfaced in the embed, 5-letter input validation, `README.md` setup + run instructions. | Simulated endpoint failure still produces a sequence via override. |

Deliberate ordering: the solver is built and proven before any network or Discord code exists, so
the guarantee in §4 is never blocked on an external dependency.

## 10. Git workflow

Gitflow. `main` holds releases, `develop` is the integration branch, work happens on
`feature/*` branches cut from `develop`.

- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`).
  **Never mention the phase** — no `Phase 1`, no `P0`, no step numbering in subject or body.
  Describe the change, not the plan position. Example: `feat: score guesses by candidate-set entropy`.
- **One commit per coherent change**; test lands with the code it covers.
- **Approval gates:**
  1. Commits are made locally without asking.
  2. `git push` — **only after explicit approval** for that push.
  3. PR creation (feature → `develop`) — permitted once the branch is pushed.
  4. PR merge — **never without explicit approval.** Same for merging `develop` into `main`.
- PR body states scope, the gate result, and the commands/tests run.
- Release: `develop` → `main`, tagged `v0.1.0`. Hotfixes branch from `main` as `hotfix/*`.

## 11. Out of scope

Honest (no-NYT-data) solver mode, interactive feedback entry, Wordle Review scraping,
multi-puzzle/variant support, "make the record look humanly imperfect" jitter, hosting/deploy
config. BRIEFING §4.8 ToS concern is noted and accepted: one request per day, personal use.
