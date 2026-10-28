# The overview sketch round: brief

**Written 2026-10-25. Status (2026-10-27): done; neither sketch chosen. The deep research followed the same day (note 26); a new look-and-react round waits on the user's choice of first view.** Approved by the user on 2026-10-24 (GOAL §2, round 2: "first research and sketch the overview"). The research pass is done ([note 25](../../research/round6/25-overview-display.md)). This brief is for whichever session runs the round. [GOAL.md](../../GOAL.md) overrides it.

## Goal

One sketch round that shows the user their overview on their own non-Northstar work, and measures it against their usual means (DESIGN §6, §8).

## Material (GOAL §2, 2026-10-25)

- **The website work.** The parsed sessions are in `~/northstar-probe/data/website-*.json`. Screenshots from the earlier human-view rounds are in `~/northstar-probe/out/hv2-img/`, with the round-2 data in `hv2-data.js`.
- **Chats the user adds** to `~/northstar-probe/inbox/`: export files, or pasted text with `Me:` and `AI:` markers. Parse them with `~/northstar-probe/tools/parse_inbox.py`. The inbox was empty on 2026-10-25; the user offered "a few chat example".
- **No Northstar content.** The test runs on other work.

## What to build

1. **Items and topics.** Extract the user's ideas and the AI ideas they adopted, per DESIGN §1.2 stages 2–3. Each item gets an exact quote, scope and origin. Group them into a few topics in the user's words, with connect and conflict links. Under each idea, put one to three pieces of their work as cues: a screenshot, a page, a commit or a file, never a path string.
2. **Two sketches, with the same items and cues** (note 25 §4):
   - **A, a topic outline with conflict pairs.**
   - **B, a stable topic map** with connect and conflict lines.

   Each has two views:
   - a small card, as Claude's inline card allows: about 4–5 data points and two actions, "Open overview" and "Ask about a topic";
   - a full-screen view.

   Both mark origin quietly (yours, or adopted from a named AI), offer one-step corrections ("not what I think", "keep", "project only"), and show "ask about this for my problem" as one step into the chat.
3. **The test page** (DESIGN §8; note 25 §5):
   - Four set tasks from the user's real topics, 5 minutes each.
   - Two use the user's usual means (their apps' chat search and memory, their repositories); two use the overview, alternating A and B.
   - Then the user flags lines that are "not what I think", says which form they prefer, and says whether they would use "ask about this".
   - Save the answers to a local text file, as the earlier rounds did (`~/northstar-probe/out/*-user-answers.txt`; see `tools/build_review_r4.py` for the pattern).

## Where it lives

- Everything stays in `~/northstar-probe/out/` and is served locally by the `probe-review` launch configuration (`localhost:8765`). Nothing is published, and no personal content enters the repo.
- Only aggregate results go to `docs/EXPLORATION.md`.

## Pass bars, fixed now (DESIGN §8)

- The overview wins at least 3 of the 4 tasks and loses none.
- At most 1 line in 10 is flagged "not what I think".
- With one rater, a pass is directional. A against B is directional only.
- Whether the user takes the "ask about this" step is the evidence for revisit-only versus expand (GOAL §2, 2026-10-24).

## Rules

- Read GOAL.md first. Never re-scope the user's goal; anything that changes a confirmed answer goes to the user as a question.
- State the token cost before any multi-agent workflow; the user has a spend limit. Plan about 0.3M tokens per research-sized agent.
- Personal probe data stays in `~/northstar-probe`.

## Done means

- Both sketches and the test page work on `localhost:8765`, and the user has been told how to open them.
- After the user does the test, the results are recorded: aggregates in EXPLORATION.md, the user's answers verbatim in GOAL.md.

## Status (2026-10-25)

- **Material:** the website work, plus three ChatGPT chats the user sent on 2026-10-25: two interview-prep chats (coding, system design) and one winter-tire purchase chat. They were moved out of the repo into `~/northstar-probe/inbox/examples-2026-10-25/` and parsed into `~/northstar-probe/data/ex-*.json`.
- **Built** in `~/northstar-probe/out/`:
  - `ov-data.js`: 4 topics, 22 ideas, 12 work cues, 2 conflicts, 8 connections and 5 open items. Every chat quote is checked verbatim by the builder.
  - `ov-a.html`: sketch A, the topic outline with conflict pairs.
  - `ov-b.html`: sketch B, the stable topic map.
  - `ov-test.html`: the test, 8 questions in 4 matched pairs, half with the user's usual means and half with a sketch, alternating A and B.
  - `ov-answer-key.json`: the answer key and the win rule, both fixed before the test.
- **Open it:** `http://localhost:8765/ov-test.html` while the `probe-review` server runs.
- **The user's README** with the chats marks focus and memory failure points (goal drift in the design mock; a seller's claim carried to the wrong listing). Keep those chats for the focus and memory tests in DESIGN §8.

## Result (2026-10-27)

- **2 wins, 2 ties, 0 losses: the bar (at least 3 wins, no losses) is missed.**
  - The sketches gave right answers on seller attribution and on a cross-context conflict, where memory or ChatGPT gave partial ones.
  - One sketch question was answered without a lookup.
- **The user's verdict, verbatim:** "Neither. Leaning towards B but still not very helpful. I asked for a deep research on what is the best form, article/papers/published etc,."
- **"Ask about this":** "I'd use it". Both tries were questions about the user's past.
- **Revisit versus expand:** still not sure.
- Answers and scoring are in `~/northstar-probe/out/ov-user-answers.txt` and `ov-results.json`.
