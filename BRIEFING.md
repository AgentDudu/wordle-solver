# Discord Wordle Solver — Discussion Brief for Coding Agent

**Purpose of this document:**  
You are a coding agent. Read this brief carefully. Then initiate a conversation with the user to resolve the open questions below. Do **not** start writing code until the user has confirmed the decisions. Your goal is to turn this brief into a concrete, unambiguous specification.

---

## 1. Project Summary

Build a Discord bot that solves the daily NYT Wordle. The bot will:

- Fetch today’s official Wordle hints (one consonant, one vowel) and the full answer from NYT sources.
- Generate a sequence of human-plausible guesses.
- Allow the user to choose whether the bot should “solve by” the 3rd or 4th attempt.
- If the accumulated feedback is not “sufficient” by that attempt, fall back to directly guessing the known answer.
- Deliver guesses (and possibly feedback) through Discord.

The core idea is a **humanlike solver** that uses the official hints as a starting point, then optimizes for yellow/green feedback until a deadline, after which it forces the answer.

---

## 2. Data Sources

- **Official hints:** The NYT Wordle Review page contains “Give me a consonant” and “Give me a vowel” buttons. The hints are revealed after the daily puzzle goes live.
- **Full answer:** A public (undocumented) NYT API endpoint returns the solution for a given date:  
  `https://www.nytimes.com/svc/wordle/v2/YYYY-MM-DD.json`
- **Word lists:** Need both the list of valid Wordle guesses (allowed guesses) and the list of possible answers. These can be sourced from open-source Wordle datasets.

**Stability concern:** Scraping the Wordle Review page is brittle (HTML changes, bot protection, authentication). The API endpoint is more stable but undocumented and could be rate-limited or removed. A fallback (e.g., local cached answer list, manual override) should be discussed.

---

## 3. Core Mechanics (Current Understanding)

1. **First guess:** Choose a random legal Wordle word that contains both the hinted consonant and the hinted vowel.
2. **Subsequent guesses:** Pick words that maximize yellow/green feedback while remaining valid Wordle guesses.
3. **Attempt limit:** User chooses either “solve by attempt 3” or “solve by attempt 4”.
4. **Fallback:** If by the chosen attempt the feedback is not “sufficient”, directly guess the known answer.
5. **Delivery:** Discord bot commands and responses.

---

## 4. Key Concepts and Choices to Discuss

### 4.1 Humanlike vs. Auto-Solver
- **Humanlike hint engine:** Suggests plausible guesses and only reveals the answer as a last resort. Never uses the fetched answer unless forced.
- **Auto-solver:** Uses the fetched answer as an oracle to guarantee solving within N attempts. The “humanlike” part is only the sequence of guesses before the forced answer.

**Decision needed:** Which behavior is primary? The current description mixes both. Clarify whether the bot is allowed to “know” the answer from the start and use it to guide guesses, or whether it should only use the answer for the final forced guess.

### 4.2 Definition of “Enough Yellow/Green”
The fallback trigger “not enough yellow or green” is subjective. Need a concrete threshold. Examples:
- At least 2 green letters?
- At least 1 green + 1 yellow?
- A combined score: `greens * 2 + yellows * 1 >= X`?
- Or simply: if the answer is not among the remaining possible words after N guesses?

**Decision needed:** Define the exact condition that triggers the forced answer.

### 4.3 Attempt Limit Semantics
User chooses “solve by the 3rd or 4th attempt”. This could mean:
- **Option A:** The bot must guess the answer on that attempt (i.e., attempt 3 or 4 is the answer).
- **Option B:** The bot must narrow it down so that the next attempt is guaranteed correct, but the actual answer is given on attempt 4 or 5.

**Decision needed:** Clarify what “solve by attempt N” means in terms of the guess sequence.

### 4.4 First Guess Strategy
- The hinted consonant and vowel are single letters. Find a 5-letter word containing both.
- Must ensure the word is in the **legal guess list**, not just the answer list.
- Should the first guess be truly random among all such words, or should it also consider letter frequency / information gain?

**Decision needed:** How to select the first guess? Random, or optimized?

### 4.5 Subsequent Guess Strategy
- “Maximize yellow/green” is a heuristic. It can be implemented as:
  - Greedy: pick the word that yields the most expected yellow/green based on remaining candidates.
  - Entropy: pick the word that splits the candidate set most evenly (standard Wordle solver).
  - Hybrid: use entropy for early guesses, then switch to candidate elimination.
- Need to define how the bot incorporates the hints into the candidate filtering.

**Decision needed:** Which algorithm should drive guesses 2..N?

### 4.6 Data Fetching Reliability
- How to handle NYT page changes or API failures?
- Should the bot cache the answer and hints daily?
- Should there be a manual override command (e.g., `!setanswer crane`)?
- Rate limiting and user-agent considerations for scraping.

**Decision needed:** Fallback and caching strategy.

### 4.7 Discord Bot UX
- Commands: `!wordle`, `!solve 3`, `!solve 4`, `!hint`, etc.
- Should the bot show the sequence of guesses with feedback (like Wordle’s colored squares)?
- Should it be per-user or per-channel?
- How to handle multiple users playing the same daily puzzle?

**Decision needed:** Command structure and interaction flow.

### 4.8 Legal and Ethical Considerations
- Scraping NYT and using their API may violate terms of service.
- Revealing the answer spoils the puzzle for users. Should there be a spoiler warning?
- Is this for personal use or public Discord servers?

**Decision needed:** Scope and compliance.

---

## 5. Open Questions for the User

Please discuss and answer the following:

1. Is the bot a **hint engine** (never uses the answer until forced) or an **auto-solver** (uses the answer as an oracle)?
2. What is the exact threshold for “enough yellow/green” that triggers the forced answer?
3. What does “solve by the 3rd/4th attempt” mean precisely? (Answer on that attempt, or guaranteed by the next?)
4. How should the first guess be chosen? Random legal word with both hints, or optimized?
5. Which algorithm should pick guesses 2..N? Greedy feedback, entropy, or hybrid?
6. How should the bot handle NYT scraping/API failures? Caching? Manual override?
7. What Discord commands and responses do you envision? (e.g., `!solve 3`)
8. Is this for personal use or a public bot? Any terms-of-service concerns?
9. Do you want the bot to display the full guess history with colored feedback?
10. Any other constraints (hosting, language, existing codebase)?

---

## 6. Suggested Next Steps

1. The coding agent should ask the user the open questions above, one by one or in a structured list.
2. Once answered, the agent should produce a finalized specification.
3. Then propose an architecture (language, libraries, Discord API, data storage).
4. Finally, implement in small iterations: data fetching → solver logic → Discord integration.

---

## 7. Revised One-Sentence Description (for reference)

> The bot fetches today’s Wordle consonant hint, vowel hint, and full answer from NYT’s Wordle Review page and public API. It generates a sequence of human-plausible guesses. The first guess is a random legal Wordle word containing both hinted letters. Subsequent guesses maximize yellow/green feedback while remaining valid. The user chooses a target attempt (3rd or 4th). If by that attempt the accumulated feedback is not “sufficient” (threshold to be defined), the bot falls back to directly guessing the known answer. The bot never reveals the answer earlier than the user’s chosen attempt unless no other legal guess exists.

---

**Agent instruction:** Start the discussion now. Ask the user to resolve the open questions before proceeding.
