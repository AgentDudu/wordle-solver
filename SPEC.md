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
2. `GET https://www.nytimes.com/svc/wordle/v2/YYYY-MM-DD.json` → `.solution`.
   Verified 2026-10-13: returns `{"id":2024,"solution":"quail","print_date":"2025-06-15",
   "days_since_launch":1457,"editor":"Tracy Bennett"}` with HTTP 200 **with and without** a
   `User-Agent` header. A browser `User-Agent` is still sent — one line of insurance against
   future bot protection, not a current requirement. One request per day.
3. Manual override command `/wordle setanswer <word>` (owner-only, see §6).

Date is resolved in `America/New_York` — NYT rolls the puzzle at midnight ET, not UTC.

### 3.2 Hints
Derived locally, never scraped. `C` = most frequent consonant present in the answer,
`V` = most frequent vowel present, frequency order `etaoin shrdlu`. Deterministic per answer.

These may differ from the letters NYT's own "Give me a consonant / a vowel" buttons reveal.
Both are true statements about the word. Accepted trade-off — it removes the brittle,
bot-protected HTML scrape described in BRIEFING §2.

### 3.3 Word lists
`data/answers.txt` — 2,315 words, one per line, lowercase, sorted. Snapshot of the classic
official NYT answer list
(`wordle-answers-alphabetical.txt`, retrieved 2026-10-13 from
`raw.githubusercontent.com/taw/100-languages-speedrun/master/episode-88-brat/`).

**Measured staleness.** Sampling 16 recent dates from the NYT endpoint, 1–2 answers fall outside
this list — `yodel` (2026-10-12) and `aspic` (2026-08-16) are absent. Roughly 6% of current
answers are new words NYT added after the snapshot was cut.

That is not cosmetic: if the true answer is outside the guess pool, the feedback-consistent
candidate set in §4 can empty out and the sequence stalls before attempt N. So the pool is
always `ANSWERS | {answer}` — the fetched answer is unioned in. One line, and it makes the
§4 guarantee hold for words the snapshot has never seen.
`shortcut: snapshot is never refreshed; the union covers today's answer only. Upgrade to a
maintained list if the pool's word quality ever matters more than the guarantee.`

## 4. Algorithm

`colorize(guess, answer)` is standard Wordle two-pass scoring: greens first, then yellows
against unmatched letters only, so duplicate letters are handled correctly.

```
score(word, pool) = entropy of the partition of `pool` by colorize(word, candidate)
                    for candidate in pool          # Shannon, base 2

sequence(answer, N):
    universe = ANSWERS | {answer}        # answer must be in the pool, see 3.3
    C, V   = hints(answer)
    pool   = [w in universe if C in w and V in w]
    if not pool: pool = universe         # shortcut: hint constraint dropped if unsatisfiable

    g1     = argmax score(w, pool) for w in pool \ {answer}
    cands  = [w in universe if colorize(g1, w) == colorize(g1, answer)]

    for k in 2 .. N-1:
        legal = [w in cands if w not in guessed and w != answer]
        if not legal: legal = [w in universe if w not in guessed and w != answer]   # filler, see below
        gk     = argmax score(w, cands) for w in legal, tie-break by list order
        cands  = [w in cands if colorize(gk, w) == colorize(gk, answer)]

    gN     = answer
    return [g1, ..., gN] with feedback colorize(gi, answer) for each i
```

Three properties the tests assert:

- **Consistency.** Every guess `gi` is a word that is still a *possible answer* given the feedback
  already seen, i.e. `colorize(gj, gi) == colorize(gj, answer)` for every earlier guess `gj`.
  Equivalently: a player who only ever sees feedback never has a guess eliminated by that same
  feedback. Copying the guess into NYT produces exactly the colours the bot printed.
- **No early reveal.** `gi != answer` for `i < N`. If the answer is the only consistent word left
  before attempt N, a filler from the universe is guessed instead — the documented exception, and
  the only case in which a guess is not consistent.
- **Convergence.** `gN == answer`, `len(sequence) == N`, and the answer is never eliminated from
  the candidate set.

Scoring pool is the surviving candidate set itself, not the whole word list. This is both
faster (≈150×150 comparisons instead of 2,315×2,315, so a sequence computes in well under a
second in pure Python) and more humanlike — humans guess from words they think are still possible.
The hint filter applies to guess 1 only; candidate tracking spans the whole universe, because a
later guess may legitimately sit outside the hint filter.

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
tests/
    test_words.py   # answer-list integrity
    test_solver.py  # full-answer-list replay, added with the solver
requirements.txt    # discord.py>=2.3   (stdlib urllib for the HTTP call, stdlib unittest for tests)
.gitattributes      # * text=auto eol=lf
.env.example        # DISCORD_TOKEN
```

`DISCORD_TOKEN` from environment. No dotenv dependency — `bot.py` reads `os.environ` directly.

## 8. Test

Stdlib `unittest`, no test dependency. Run: `python -m unittest discover -s tests`.

`tests/test_words.py` asserts `data/answers.txt` is 2,315 unique five-letter lowercase words.

`tests/test_solver.py` replays the answer list for N = 3 and N = 4 and asserts: sequence length
is N, last guess is the answer, no guess repeats, every guess is in the pool, guess 1 contains
both hint letters, and — the load-bearing one — a simulated player who only ever sees feedback
never has a guess eliminated by that feedback and never loses the answer from the candidate set.
The exception rule is asserted too: an inconsistent guess is permitted only when the live set has
collapsed to the answer alone.

The default run samples every 100th answer (~24 answers, ~8 s for the whole suite). The full
sweep over all 2,315 answers costs minutes, so it is opt-in: `WORDLE_REPLAY_ALL=1`. It also
replays `yodel` and `aspic`, deliberately absent from `data/answers.txt`, to prove the
`ANSWERS | {answer}` union in §3.3 holds. This test *is* the guarantee, made executable.

## 9. Implementation phases

Each phase is independently verifiable and lands on its own branch/PR. Nothing moves to the next
phase until the current phase's gate passes.

| Phase | Branch | Deliverable | Gate |
|---|---|---|---|
| **P0 — scaffold** | `feature/repo-scaffold` | Package layout, `requirements.txt`, `data/answers.txt`, `.gitignore`, `.gitattributes`, `.env.example`, `tests/test_words.py`. | `python -m unittest discover -s tests` passes offline; no solver code yet. |
| **P1 — solver core** | `feature/solver-core` | `solver.py`: `colorize`, `score`, `hints`, `sequence`, `render`. `tests/test_solver.py` replay + `colorize` cases. | Sampled replay passes for N=3 and N=4; `WORDLE_REPLAY_ALL=1` sweep passes. Runs offline. |
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
