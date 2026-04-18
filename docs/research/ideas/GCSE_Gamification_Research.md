# GCSE English AI Tutor: Gamification Research

Research notes from early ideation conversations — January 2026

## 1. The Core Problem: Single-User Gamification

Traditional study guides go unused because they are passive. The idea of adding gamification (inspired by Duolingo) was raised early, but with an important caveat: Duolingo's core mechanics rely heavily on social pressure and competition via leaderboards and streaks compared against friends. With a single user, those social mechanics fall flat quickly.

The key insight reached in early ideation:

- Gamification for a solo user must focus on personal growth, not competition.
- Beating your past self, unlocking achievements, and building personal streaks can be as motivating as leaderboards.
- AI companions (Reachy robot) reacting to progress adds a social-feeling dimension without requiring other users.

## 2. Core Gamification Mechanics Proposed

### 2.1 XP (Experience Points) System

Every study session awards XP based on performance. Example values discussed:

- Macbeth session completion: +180 XP
- Daily challenge tasks: +30 to +50 XP each
- Achievement unlocks: variable XP reward
- Boss Battle completion: +1000 XP

### 2.2 Levels & Titles

A named level progression system provides a sense of identity and progression. Example from the dashboard mockup:

- Level 14 title: "Scholar"
- Level 15 unlocks: Boss Battle mode
- XP thresholds: 1,800 XP to next level was cited as an example

### 2.3 Streaks

Daily study streaks were a core mechanic, with Reachy able to report on them conversationally. Example scenario:

- "She has a 12-day streak — her longest yet!"
- Achievement: "Fortnight Force" — 14 consecutive days

### 2.4 Achievement Categories

Six achievement categories were defined in the Python prototype:

- Consistency — Streaks and regular practice
- Mastery — Topic completion (e.g. "Macbeth Master" at 100% coverage)
- Growth — Improvement over time
- Exploration — Trying different topics/texts
- Challenge — Completing hard or timed tasks
- Milestone — XP and level thresholds

### 2.5 Named Achievements (Examples)

- "Quote Champion" — Use 10 embedded quotations in sessions
- "Macbeth Master" — 100% topic coverage on Macbeth
- "Fortnight Force" — 14-day consecutive study streak
- "Poetry Pioneer" — Complete 2 sessions on Power & Conflict Poetry
- "Exam Ready" — Complete a Boss Battle timed challenge (trophy reward)

### 2.6 Daily Challenges

A set of rotating daily mini-goals keeps sessions purposeful:

- Complete one session (any topic): +50 XP
- Practice a quotation analysis: +30 XP
- Review yesterday's mistakes: +40 XP

### 2.7 Quests / Weekly Goals

- Weekly session goal: e.g. 4 sessions per week (progress bar shown on dashboard)
- Timed quests with expiry dates: e.g. "Complete 2 sessions on Power & Conflict Poetry" with a 3-day timer and 500 XP + badge reward

### 2.8 Boss Battle Mode

Unlocked at Level 15, Boss Battle mode introduces timed, exam-style challenges. Framed as "the final boss" — tests everything learned under exam-like conditions. Intended as a high-stakes, high-reward experience that prepares for real GCSE assessment. Reward: 1,000 XP + Exam Ready trophy.

## 3. Reachy Robot as Gamification Companion

A key differentiator discussed was using the Reachy Mini robot ("Scholar") as a social-feeling gamification companion. Rather than a static UI, Reachy verbally reports progress, reacts to achievements, and provides encouragement. This addresses the single-user isolation problem by creating an AI companion that responds to the student's progress.

Example scenarios explored:

- Parent query: "How's Eleanor's revision going?" → Reachy reports streak, level, recent XP, and upcoming achievements in natural speech
- Student query: "What achievements am I close to?" → Reachy identifies the 2-3 nearest unlockable achievements and suggests a targeted session

## 4. Cross-Session Memory & Adaptive Difficulty

Gamification was designed to integrate with the shared Graphiti knowledge graph memory, enabling:

- Persistent XP, level, and streak state across sessions (student never starts fresh)
- Tutor adapts difficulty based on accumulated knowledge of strengths and weaknesses
- Parent preferences (e.g. "responds better to encouragement than criticism") propagate to the tutor's feedback style
- Reachy can report on GCSE progress as part of the wider Ship's Computer dashboard

## 5. Dashboard Concept

A progress dashboard was sketched showing Eleanor's GCSE status alongside other Ship's Computer agents. Key elements:

- Streak counter and current level/title
- Weekly session goal progress bar
- Active quest panel with expiry timers
- Boss Battle unlock progress (XP to next level)
- Daily challenge checklist (+XP per task)
- Activity log showing completed sessions, XP earned, and agent events

## 6. Study Buddy / Social Workaround

To partially compensate for the absence of real social competition, a "Study Buddy" concept was introduced: named AI companion characters with distinct personalities (avatars, names, closing messages) that react to session outcomes. Not other students, but still a social-feeling presence within the system.

---

*Source: Conversation from 30 January 2026 — https://claude.ai/chat/d9b1df40-7fba-471e-884b-905f40593cd1*
