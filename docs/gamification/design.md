# GCSE Study Tutor — Gamification Design

**Status:** Phase 0 authoritative draft. Economy is fixed; state engine is
Phase 2.
**Owner:** Rich Woollcott.
**Consumers:** `docs/research/ideas/phase-0-build-plan.md` FEAT-PO-001,
Phase 2 FEAT-PO-007 (gamification state engine), Phase 2 dashboard,
Reachy Mini companion scripts.
**Authoritative sources:** `GCSE_Gamification_Research.md`,
`gemma4-hackathon-submission-plan.md §5`.
**Status of implementation:** design only — no state engine exists in
Phase 0. This document is the contract the Phase 2 engine is built against.

---

## 1. The core problem and the design principle

AI tutors fail not because the model cannot answer questions. They fail
because teenagers do not open them. Revision guides gather dust for the
same reason. Duolingo-style gamification works — at scale — because of
social pressure: leaderboards against real friends, streaks you can see
broken in your feed, competitive urgency tied to identity.

**With a single user at home, those social mechanics fall flat.** A
leaderboard of one is not a leaderboard. A streak nobody else sees is
just a number.

### The design principle

Gamification for a solo learner is about **personal growth, not
competition**. Specifically:

- Beating your past self.
- Building personal streaks that feel earned.
- Unlocking named progression that signals identity.
- Having an AI companion (Reachy Mini "Scholar") that reacts to your
  progress in natural speech, creating a social-feeling dimension
  without other users.

This is not a workaround for lack of a social graph. It is a different
and — for a single learner — arguably more durable engagement model.
Progress that is meaningful to you personally does not need ranking
against others to matter.

---

## 2. XP economy

XP (experience points) is the single scalar currency. Every engagement
event awards XP. XP is persistent across sessions via Graphiti (Phase 1).

### 2.1 Session XP

| Event | XP | Notes |
|---|---|---|
| Complete a study session (short, ~10 min, single topic) | +60 | Base value |
| Complete a standard study session (~20 min) | +120 | |
| Complete a long study session (~30–40 min, full essay scaffold or multi-topic) | +180 | Example from research: a Macbeth session +180 |
| Complete a session that includes quotation practice | +30 bonus | Stacks with above |
| Complete a session that includes review of previous mistakes | +40 bonus | Stacks; rewards spaced repetition |
| Session abandoned < 2 min | 0 | No XP for taps without engagement |

Difficulty scaling: if the session contains Grade 8–9 target scaffolding,
XP is multiplied by 1.25 (rounded up). This keeps the incentive to stretch
for higher grade targets rather than stay in easy territory.

### 2.2 Daily challenge XP

Each day, 3 rotating mini-goals are offered. Each can be completed once
per day. Full list:

| Challenge | XP | Frequency |
|---|---|---|
| Complete at least one session (any topic) | +50 | Daily |
| Practise a quotation analysis (embed + analyse one quote) | +30 | Daily |
| Review yesterday's mistakes (re-attempt one error flagged last session) | +40 | Daily |
| Try a new topic (one not studied in the last 7 days) | +40 | Daily |
| Complete an unseen-passage analysis | +50 | Daily |

The daily challenge panel picks 3 at random from the pool each day. Hit
all 3 and you earn a **daily sweep bonus** of +20 XP.

### 2.3 Quest XP (weekly goals)

Weekly quests run for a named expiry window, usually 3 or 7 days.
Example from research: *"Complete 2 sessions on Power and Conflict
Poetry — 3-day timer — 500 XP + Poetry Pioneer badge."*

| Quest shape | XP reward | Typical duration |
|---|---|---|
| Topic focus quest (complete N sessions on a named topic/text) | +500 | 3 days |
| Skill focus quest (complete N sessions exercising a named AO) | +400 | 5 days |
| Streak quest (study on N consecutive days) | +300 | 7 days |
| Exam-technique quest (complete N timed sections) | +600 | 7 days |

Quests run one at a time for Phase 2 MVP. If a quest expires
uncompleted, no XP is awarded and no penalty is applied; the quest is
gone.

### 2.4 Boss Battle XP

Boss Battles are timed, exam-style challenges. They are the "final boss"
of the gamification economy.

- Completion of a Boss Battle: **+1000 XP**
- Trophy awarded: **Exam Ready**
- Difficulty-scaled Boss Battles (Boss Battle Hard, introduced later in
  the curriculum): +1500 XP

Boss Battle unlocks at **Level 8**, is not repeatable for XP more than
once per calendar week (the first completion each week awards XP; later
completions award no XP but are unlocked for practice).

### 2.5 Achievement XP

Named achievements award XP on first unlock. Variable per achievement;
values enumerated in §5.

---

## 3. Levels and titles (15 levels)

The level progression is the identity axis. Each level has a named
title; each level unlocks something. Named titles come from the hackathon
submission plan (§5.2 of `gemma4-hackathon-submission-plan.md`).

### 3.1 Level titles and XP thresholds

| Level | Title | Total XP to reach | XP in level |
|---|---|---|---|
| 1 | **Beginner** | 0 | 100 |
| 2 | **Novice** | 100 | 200 |
| 3 | **Apprentice** | 300 | 300 |
| 4 | **Student** | 600 | 400 |
| 5 | **Learner** | 1000 | 500 |
| 6 | **Scholar** | 1500 | 700 |
| 7 | **Academic** | 2200 | 900 |
| 8 | **Intellectual** | 3100 | 1100 |
| 9 | **Expert** | 4200 | 1400 |
| 10 | **Master** | 5600 | 1700 |
| 11 | **Sage** | 7300 | 2100 |
| 12 | **Virtuoso** | 9400 | 2500 |
| 13 | **Luminary** | 11900 | 3000 |
| 14 | **Prodigy** | 14900 | 3600 |
| 15 | **Grandmaster** | 18500 | — (terminal) |

The curve is gently exponential — small levels early to give fast
feedback, progressively larger thresholds later so that reaching
Grandmaster is a genuine season-of-revision achievement, not a
one-weekend grind.

The research doc (`GCSE_Gamification_Research.md §2.2`) references
"1,800 XP to next level" and a dashboard mock at **Level 14 (Scholar) with
Level 15 unlock = Boss Battle**. The named progression above supersedes
those example numbers — they were sketches before the 15-level scheme was
finalised. The authoritative titles and unlock gates are §3.2 below.

### 3.2 Unlock gates (what each level unlocks)

| Level | Unlock |
|---|---|
| 1 | Base tutoring: sessions, XP, streaks |
| 2 | **Daily challenges panel** becomes active |
| 3 | Topic mastery dashboard becomes visible |
| 4 | Quest system becomes active (one quest at a time) |
| 5 | Per-AO progress breakdown |
| 6 | **Exam-style practice questions** (synthetic, in AQA style) |
| 7 | Comparative-essay scaffold mode |
| 8 | **Boss Battle mode** (timed exam-style challenges) |
| 9 | Two concurrent quests allowed |
| 10 | **Teaching Mode** (student explains a concept back to the tutor, tutor evaluates) |
| 11 | Cross-text comparison mode (linking themes across set texts) |
| 12 | Custom practice builder (student designs their own prompt) |
| 13 | Boss Battle Hard (difficulty-scaled timed exam) |
| 14 | Companion voice (Reachy Mini expanded progress reporting — gated on Reachy hardware) |
| 15 | Grandmaster status — all modes unlocked, post-Grandmaster achievements become the progression |

Unlocks are one-way. Once unlocked at a level, they remain available even
if the XP economy is ever rebalanced downward (which it shouldn't be).

---

## 4. Streaks

Daily streak — number of consecutive calendar days on which at least one
session was completed.

### 4.1 Streak mechanics

- Streak increments on completion of any session (not an abandoned one).
- Streak resets to 0 at midnight of any day without a session completion.
- **Streak freeze** (optional, Phase 2.5+): one streak freeze per week,
  earned automatically. Applies automatically to the first missed day
  in any given week. This reduces the brittleness of streaks without
  eliminating the daily pull.
- **Longest streak** — persisted separately. Resets only via explicit
  data wipe.

### 4.2 Streak milestones (achievements)

See §5, Consistency category, for the named streak achievements.
Milestones at: **3 days**, **7 days**, **14 days** (Fortnight Force),
**30 days**, **60 days**, **100 days**.

---

## 5. Achievements

Six categories, aligned with `GCSE_Gamification_Research.md §2.4`:

1. **Consistency** — streaks and regular practice
2. **Mastery** — topic completion
3. **Growth** — improvement over time
4. **Exploration** — breadth across texts/topics
5. **Challenge** — completing hard or timed tasks
6. **Milestone** — XP and level thresholds

Named achievements below. Each achievement is awarded at most once per
student; progress is trackable (near-miss state is visible on the
dashboard and by Reachy).

### 5.1 Consistency

| Achievement | Criterion | XP | Notes |
|---|---|---|---|
| **First Steps** | Complete 1 session | +50 | First session ever |
| **Three Day Run** | 3-day streak | +100 | |
| **Week One** | 7-day streak | +200 | |
| **Fortnight Force** | 14-day streak | +400 | Named in research doc |
| **Thirty Days** | 30-day streak | +800 | |
| **Sixty Strong** | 60-day streak | +1200 | |
| **Century** | 100-day streak | +2000 | |
| **Morning Star** | 5 sessions before 09:00 | +150 | Encourages early-morning revision |
| **Evening Scholar** | 5 sessions after 19:00 | +150 | Encourages post-homework study |

### 5.2 Mastery

Topic mastery uses the confidence taxonomy in §6. An achievement at a
named topic is awarded at **80% confidence** per the hackathon plan §5.2.

| Achievement | Criterion | XP | Notes |
|---|---|---|---|
| **Macbeth Master** | 80% confidence on Macbeth | +500 | Named in research + hackathon plan |
| **Poetry Pioneer** | Complete 2 sessions on Power & Conflict poetry | +300 | Named in research |
| **Poetry Progenitor** | 80% confidence across full Power & Conflict cluster | +700 | |
| **Christmas Carol Champion** | 80% confidence on A Christmas Carol | +500 | If studied |
| **Inspector's Apprentice** | 80% confidence on An Inspector Calls | +500 | If studied |
| **Jekyll & Hyde Savant** | 80% confidence on Jekyll and Hyde | +500 | If studied |
| **Language Paper 1 Veteran** | 10 completed Language Paper 1 sections | +400 | |
| **Language Paper 2 Veteran** | 10 completed Language Paper 2 sections | +400 | |
| **Unseen Ready** | 80% confidence on unseen poetry approach | +500 | |

Mastery achievements for any 19th-century novel, modern text, or
Shakespeare text are generated from the same 80%-confidence rule when
the student opts into that text in session context. The named ones
above are pre-curated for the most common United Learning choices.

### 5.3 Growth

| Achievement | Criterion | XP | Notes |
|---|---|---|---|
| **Climbing** | 10% confidence increase on any named topic in one week | +200 | Rewards improvement, not absolute level |
| **Breakthrough** | 25% confidence increase on any named topic in one week | +500 | |
| **No Weak Spots** | No topic below Developing (≥40% confidence) across all studied topics | +600 | |
| **Comparative Climber** | Write a first comparative paragraph rated ≥ the student's baseline analytical writing | +300 | Growth on AO3 |
| **Quote Champion** | Use 10 embedded quotations across sessions | +250 | Named in research doc |
| **Quote Master** | Use 50 embedded quotations across sessions | +600 | |

### 5.4 Exploration

| Achievement | Criterion | XP | Notes |
|---|---|---|---|
| **Set Text Explorer** | Study sessions on 3 different set texts | +200 | |
| **Genre Gatherer** | Study sessions across poetry, drama, prose in the same week | +300 | |
| **Historical Horizon** | Complete sessions on 19th-century novel, Shakespeare, and modern drama | +400 | |
| **Six-AO Sampler** | Have at least one session where each of AO1–AO6 was scaffolded within it | +500 | |

### 5.5 Challenge

| Achievement | Criterion | XP | Notes |
|---|---|---|---|
| **Exam Ready** | Complete a Boss Battle | +500 + Trophy | Trophy is visible separately from XP |
| **Exam Ready Hard** | Complete a Boss Battle Hard | +800 + Trophy | Level 13+ |
| **Timed Analysis** | Complete 5 timed Paper 1 Q4 evaluations | +300 | |
| **Full Paper** | Complete a full mock Paper 1 (all 4 questions in one sitting) | +600 | |
| **Pressure Test** | 3 Boss Battles in a single week | +1000 | Unlocked when 2 concurrent quests are active (Level 9+) |

### 5.6 Milestone

| Achievement | Criterion | XP | Notes |
|---|---|---|---|
| **First Century** | 100 XP total | +50 | |
| **Kilo** | 1,000 XP total | +100 | |
| **Five Kilo** | 5,000 XP total | +250 | |
| **Ten Kilo** | 10,000 XP total | +500 | |
| **Grandmaster** | Reach Level 15 | +2000 | Terminal milestone |
| **Scholar** | Reach Level 6 | +300 | Title-flavoured |
| **Master** | Reach Level 10 | +700 | |

---

## 6. Topic mastery — confidence taxonomy

Per-topic confidence is a number in [0, 1] maintained in Graphiti
(Phase 1). It drives adaptive session recommendations and the mastery
achievements. Confidence is displayed as a coloured bar on the
dashboard.

### 6.1 Confidence bands

| Band | Range | Dashboard colour | Reachy phrasing | Interpretation |
|---|---|---|---|---|
| **Struggling** | 0 ≤ c < 0.4 | red | "needs more work" | Student consistently missing AO targets on this topic |
| **Developing** | 0.4 ≤ c < 0.6 | amber | "coming along" | Student grasps the basics but analysis is shallow or inconsistent |
| **Secure** | 0.6 ≤ c < 0.8 | blue | "feeling confident" | Student produces Grade 6-equivalent responses reliably |
| **Mastered** | 0.8 ≤ c ≤ 1.0 | green | "really strong" | Student produces Grade 7+ responses; mastery achievement is earned at entry to this band |

### 6.2 Confidence update rule

Confidence is updated at session end by the Coach (Phase 1). The Player
generates a session summary with per-AO observations; the Coach maps
those observations to a proposed confidence delta per topic, capped at
±0.1 per session. Students cannot permanently lose a mastery achievement
even if confidence drops back below 0.8 — achievement unlocks are
sticky.

### 6.3 Adaptive session recommendation

The session planner (Phase 1 FEAT-PO-005 in the Phase 1 roadmap) uses
the confidence distribution to recommend the next session:

- If any topic is **Struggling** (< 0.4), recommend that topic next.
- Else recommend the **weakest topic below Mastered** that has not been
  studied in the last 3 days.
- Rotate to ensure exploration; do not recommend the same topic 4 days
  in a row.

---

## 7. Daily challenges (rotating daily goals)

As §2.2. The panel picks 3 from the pool each day (seeded by date +
student ID for reproducibility). Completion is tracked per calendar day.
Completion confetti + daily sweep bonus (+20 XP) if all 3 hit.

**Challenge pool (Phase 2 MVP — expanded over time):**

1. Complete at least one session — +50 XP
2. Practise a quotation analysis (embed + analyse one quote) — +30 XP
3. Review yesterday's mistakes — +40 XP
4. Try a new topic (not studied in last 7 days) — +40 XP
5. Complete an unseen-passage analysis — +50 XP
6. Write one timed analytical paragraph (under 15 minutes) — +50 XP
7. Complete a session scaffolding AO3 (comparison) — +40 XP
8. Complete a session scaffolding AO5 (writing craft) — +40 XP

---

## 8. Boss Battle mode

Timed, exam-style challenges framed as "the final boss" of a topic.
Unlocked at **Level 8**.

### 8.1 Boss Battle shapes

| Shape | Duration | XP | Trophy |
|---|---|---|---|
| Literature Paper 1 Section A (Macbeth) | 50 minutes | +1000 | Exam Ready |
| Literature Paper 1 Section B (19th-C novel) | 45 minutes | +1000 | Exam Ready |
| Literature Paper 2 Section A (modern text) | 45 minutes | +1000 | Exam Ready |
| Literature Paper 2 Section B (anthology comparison) | 45 minutes | +1000 | Exam Ready |
| Language Paper 1 full | 1h 45m | +1500 | Exam Ready |
| Language Paper 2 full | 1h 45m | +1500 | Exam Ready |

### 8.2 Scoring

Boss Battles produce a Coach-evaluated score against the relevant AO
weighting for that section, presented as a band descriptor (e.g.
"solidly in the upper band" rather than a specific grade). The student
does not see a predicted grade; see `GOAL.md §6.1`.

### 8.3 Practice mode

After first completion, the Boss Battle is available indefinitely in
practice mode. Practice mode gives no XP (per §2.4) but does update
confidence per topic.

---

## 9. Reachy Mini "Scholar" — gamification companion

Reachy Mini is the embodied gamification dimension. Hardware is on order;
scripting begins when the unit arrives. Scheduled work gated to 4 May 2026
per DEC-06 in the decisions log.

### 9.1 What Reachy does

Reachy reads Graphiti state and the gamification economy to produce
conversational progress updates. Scripts are derived from this design
doc, not hand-written per interaction.

Reachy scenarios (from `GCSE_Gamification_Research.md §3`):

- **Parent query.** *"How's Lilymay's revision going?"* → Reachy replies
  with current level title, current streak, XP earned this week, and
  one near-unlockable achievement. Example: *"She's a Scholar at Level
  6, with an 8-day streak — her longest yet. She's earned 640 XP this
  week and is two sessions away from Poetry Pioneer."*
- **Student query: near-unlocks.** *"What achievements am I close to?"*
  → Reachy identifies the 2–3 nearest unlockable achievements based on
  current confidence, streak, and XP, and suggests a targeted session.
- **Celebration.** Streak milestones, level-ups, and mastery unlocks
  trigger short celebratory acknowledgements with Reachy's head/eye
  animations. Not more than once per event.
- **Gentle encouragement.** If the streak is at risk (no session today
  by 20:00), Reachy can offer *"A short session would keep your
  [N]-day streak going."* Configurable — off by default to avoid
  nagging.

### 9.2 What Reachy does not do

- Tutor. Reachy is the companion layer; the tutoring model is separate.
- Report to anyone but household users. No cloud sync of progress.
- Apply pressure. No shame-inducing language, no "you broke your
  streak" — just facts.

---

## 10. Dashboard

The Phase 2 dashboard is static HTML generated via Claude Design (one
evening of work, Phase 2). The gamification elements on the dashboard
are:

1. **Current level + title + progress bar to next level** (prominent)
2. **Current streak + longest streak**
3. **This week's XP** (vs previous week as context)
4. **Active quest panel** (up to 2 quests at Level 9+, 1 below)
5. **Daily challenge checklist** (3 items, +XP per completion, sweep
   bonus indicator)
6. **Topic mastery grid** — one confidence bar per studied topic, colour
   per §6.1
7. **Boss Battle unlock progress** (XP to next level if below Level 8;
   Boss Battle selector if at/above)
8. **Recent achievements** (last 5, with unlock dates)
9. **Near-unlocks** (2–3 achievements closest to being earned, with
   "what gets you there" one-liner)

The dashboard is read-only. Actions (start session, accept quest, pick
Boss Battle) happen in the MCP interface, not the dashboard.

---

## 11. Persistence model (for Phase 1 Graphiti design)

This is a forward reference — the state engine is Phase 2, but
the Graphiti schema decisions need to land in Phase 1.

### 11.1 Entities (proposed)

- **Student** — one per user; holds name, current level, total XP,
  current streak, longest streak.
- **Topic** — per studied text/topic; holds confidence (0.0–1.0), last
  studied date, session count.
- **Achievement** — the set of named achievements in §5; unlocked-at
  date per student.
- **Quest** — active and historical quests with expiry and completion
  status.
- **Session** — each study session as an episode, with XP earned and
  AOs scaffolded.

### 11.2 Events driving state change

- `session.completed` → XP delta, streak delta, confidence delta per
  topic, possible achievement check, possible daily challenge
  completion.
- `achievement.unlocked` → XP delta, achievement record.
- `quest.completed` / `quest.expired` → XP delta or no-op.
- `boss_battle.completed` → XP delta, trophy, confidence delta, possible
  Exam Ready achievement.

All state changes are atomic at the session-end boundary. Within-session
state (partial progress toward a challenge) lives in session-scoped
memory only.

---

## 12. What Phase 0 delivers vs what's deferred

### Phase 0 (now, 19–20 April)

- This document.
- Nothing else. No state engine, no dashboard, no Reachy scripts.

### Phase 1 (next weekend, 26–27 April + week)

- Graphiti entity/episode schema per §11.
- Session-end hook in the Coach that emits the events in §11.2.
- Persistence-only, no UI.

### Phase 2

- Gamification state engine reading/writing Graphiti.
- Dashboard per §10.
- Reachy scripts per §9 (hardware-gated to 4 May).

### Phase 3 / post-hackathon

- Multi-subject expansion (Maths, French, Spanish) adds subject-scoped
  mastery achievements.
- Streak freeze (§4.1 optional mechanic).
- Challenge pool expansion beyond the 8 in §7.

---

## 13. Why these specific numbers

The XP values, level thresholds, and achievement criteria here come
from two sources:

1. **Direct extraction from the research docs.** Where a concrete
   number is given in `GCSE_Gamification_Research.md` (180 XP for a
   Macbeth session, 1000 XP for Boss Battle, 50 XP for daily challenge,
   14-day Fortnight Force) it is preserved verbatim. Where the hackathon
   submission plan refines a number (15-level progression with named
   titles, 80% confidence threshold for Mastery achievements), it
   supersedes.
2. **Synthesised defaults.** The level XP curve, intermediate streak
   milestones, the challenge pool beyond the 3 named in research, the
   Growth category achievements, and the Boss Battle shape menu were
   synthesised as Phase 2 MVP defaults aligned to the design principle
   in §1. These are marked conservatively — the Phase 2 state engine
   can be tuned against real observed play without breaking the design
   contract.

The economy is **balanceable but not random.** Changes should go through
the same revision gate as GOAL.md (§10 of that file) because the Coach's
assessment of session quality feeds directly into confidence updates and
therefore into achievement unlocks.

---

## 14. What this is NOT

Not a motivational toolbox. Not a pressure mechanism. Not an imitation of
Duolingo.

A teenager revising at home does not need nagged. She needs a system that
notices when she has done good work, reflects it back in terms that feel
real ("you've moved from Developing to Secure on Macbeth's soliloquies"),
gives her a companion that cares about the outcome, and gets out of the
way when she doesn't want to engage. That's the whole design.

---

*Draft: Phase 0 weekend, 19 April 2026. Authoritative on numbers; Phase 2
engine implements; Phase 3+ tuning only.*
