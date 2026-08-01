# study-tutor — read this first

**THE TWO SOURCES OF TRUTH for this repo (ground every session here before acting):**

1. **The mission** — why the tutor exists, who it serves, the laws, the measurables:
   [`docs/study-tutor-mission-statement-2026-08-01.md`](docs/study-tutor-mission-statement-2026-08-01.md)
2. **THE PLAN** — the current honest state map, the lanes, and what to do next:
   [`docs/study-tutor-plan-of-record.md`](docs/study-tutor-plan-of-record.md)

Everything else (ADRs, contracts, runbooks, research, handoffs) is INPUT to those two. If a
decision isn't reflected in the mission or the plan, update THEM — never write a new orphan
planning doc. Sessions end by updating the plan's lane step or cell they moved.

The software-factory side of this repo's life (build mechanics, factory lanes) is governed by
ai-transition's pair: `software-factory-mission-statement-2026-07-25.md` +
`software-factory-plan-of-record.md`.

Quick facts a session always needs:

- Monorepo: Python backend `src/study_tutor/` + Flutter app `app/`. Robot integration lives
  in the `fleet-gateway` repo on the robot's own host (not a sibling checkout here).
- Hermetic test run: `uv run pytest -m "not integration and not live and not keycloak" -q`
  (one named pre-existing failure is allowed — see the plan's Suites row).
- App-facing HTTP surface is a frozen contract at pinned SHAs:
  `docs/design/contracts/API-session-http-binding.md` §7 — additive or re-pin, never silent
  edits.
- Broker isolation is standing for build lanes: never connect to any NATS broker
  (no `nats://`, no `:4222`) — operator runbooks are exempt.
- The `.claude/CLAUDE.md` in this repo is GuardKit template boilerplate about the task
  workflow; it is NOT project truth — this file and the two docs above are.
