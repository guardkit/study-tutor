---
id: TASK-SMP3-06
title: "MCP adapter cutover — swap the 4 tools onto SessionService (surface byte-for-byte unchanged)"
task_type: feature
feature_id: FEAT-SMP-003
wave: 6
implementation_mode: task-work
complexity: 6
dependencies: [TASK-SMP3-05]
parent_feature_spec: features/durable-cross-device-sessions/durable-cross-device-sessions_summary.md
---

## Objective

Cut the MCP adapter's 4 session tools over from the in-memory `SessionStore` onto the durable
`SessionService`, in ONE atomic change, keeping the MCP + NATS surface **byte-for-byte unchanged**. This is
the regression-critical task: the tool names, descriptions, error envelopes, and NATS aliases must not move.

The adapter is `src/study_tutor/mcp/adapter.py`; the 4 tools are registered in `mcp/server.py:26-52`.

## Scope

**In scope — swap each tool onto SessionService (resolved via session.provider.get_session_service, or an
injected service for tests; fail fast at boot if unwired per provider.py):**
- `tutor_start_session` (`adapter.py:213`): still call `plan_session(...)` for `plan_summary`, but create the
  durable session via `SessionService.start_session(student_id=resolve_student_id(), subject=<the tool's
  student_id arg — today's subject value, ASSUM-002>, topic=topic_override)`. Return the SAME shape
  `{"session_id": <durable id>, "plan_summary": {...}}`. Identity = `resolve_student_id()` (SMP3-04), NOT the slug.
- `tutor_turn` (`adapter.py:309`): call `SessionService.turn(student_id=..., session_id=..., user_message=...,
  reply_fn=<the injected tutor/orchestrator loop>)`. Wrap today's inline orchestrator/Phase-0 reply logic
  (`adapter.py:340-380`) as the `reply_fn: ReplyFn` (returns `TutorReply(response, metadata)`). Return the SAME
  shapes (Phase-0 `{"tutor_response"}`; orchestrator `{"tutor_response","decision","attempts",...}`).
- `tutor_session_status` (`adapter.py:382`): `SessionService.session_status(...)` → return the SAME
  `{"session_id","status","turn_count","started_at"(isoformat)}` shape.
- `tutor_session_end` (`adapter.py:396`): `SessionService.end_session(student_id=..., session_id=...,
  completion=build_session_completion(...) if turn_count>0 else None)` (SMP3-05 producer; I-T6 zero-turn →
  None). Emit `session.completed` via the event bus with the PRESERVED payload (session_end.py:440-450 shape),
  emit BEFORE any post-write (DDR-003 ordering). Return the SAME `{"session_id","status":"ended"}`.
- Map `SessionService` exceptions to the existing envelopes: `SessionNotFoundError` →
  `{"error","error_type":"SessionNotFoundError"}` (`_session_not_found()`), `SessionEnded` →
  `{"error","error_type":"SessionEnded"}`, `SessionForbidden` → `{"error","error_type":"SessionForbidden"}`.
  Import `SessionNotFoundError` from `session.errors` (it subclasses KeyError, so residual `except KeyError` still works).
- Stop using the in-memory `session.tutor_session.SessionStore` and the old `perform_session_end` +
  fire-and-forget `record_topic_confidence_update` Graphiti end path.

**Out of scope**
- Deleting `session/tutor_session.py` and the graph write plumbing → FEAT-SMP-004 (the module stays; just unused).
- Changing tool names/args/descriptions or the NATS alias map — those are FROZEN (ASSUM-005).
- HTTP/WS transport / turn_stream (mobile /goal).

## Acceptance Criteria

- [ ] The 4 tool names, args, and descriptions are unchanged (incl. `tutor_session_end` = "Marks session ended."
      and the SR-07 rule that "graphiti"/"async" never appear); `mcp/server.py` still registers exactly those 4.
- [ ] `tutor_start_session` returns `{session_id, plan_summary}` with the session_id from the DURABLE session;
      the session is created via SessionService with identity = `resolve_student_id()` (not the planner slug).
- [ ] `tutor_turn` persists the user + tutor turns durably (via SessionService.turn's reply_fn) and returns the
      unchanged Phase-0 / orchestrator response shapes; a turn on an ended session returns
      `{"error_type":"SessionEnded"}`.
- [ ] `tutor_session_status` returns `{session_id, status, turn_count, started_at}` unchanged.
- [ ] `tutor_session_end` returns exactly `{"session_id","status":"ended"}`, writes the learner-state completion
      via SessionService (turn_count>0) or transitions only (turn_count==0, I-T6), and emits `session.completed`
      with the preserved payload before the write.
- [ ] Unknown/forbidden/ended sessions map to the existing `{error, error_type}` envelopes; ownership uses
      `resolve_student_id()` as the key.
- [ ] The NATS alias map (`tutor_start_session→start_session`, `topic→topic_override`) still resolves unchanged.
- [ ] `tests/unit/mcp/test_adapter.py` and `tests/unit/adapters/test_command_router.py` pass unchanged (the
      surface regression gate); the adapter no longer imports/uses the in-memory SessionStore.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
docker run -d --rm --name smp3-06-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head
# THE surface regression gate — must stay green:
.venv/bin/python -m pytest tests/unit/mcp/test_adapter.py tests/unit/adapters/test_command_router.py -v
.venv/bin/python -m pytest tests/unit -q          # composition guard
.venv/bin/ruff check src/study_tutor/mcp/adapter.py
docker stop smp3-06-pg
```

## Implementation Notes

- Inject the SessionService like the store is injected: `MCPAdapter(..., session_service=None)` defaulting to
  `get_session_service()`; tests pass `SessionService(store=FakeStudentStore())`. Per provider.py, an unwired
  service at boot is a fail-fast (not a silent in-memory fallback) — but tests always inject one.
- `reply_fn` wrapping is the trickiest bit: today `tutor_turn` runs the orchestrator/Phase-0 loop inline and
  appends turns itself. After the swap, `SessionService.turn` owns the two `append_turn` calls; the loop becomes
  `reply_fn(user_message) -> TutorReply`. Keep the metadata (decision/attempts/…) on `TutorReply.metadata` and
  re-project it into the unchanged response dict.
- `session.completed`: keep emitting the EXACT dict from `tutoring/session_end.py:440-450` (subject_slug from the
  session's subject, topics_covered/aos_exercised from the cached plan, started_at/ended_at isoformat), and keep
  emit-before-write ordering (DDR-003). Preserve the I-T6 zero-turn suppression (no emit, no write).
- Do NOT change `roles/tutor/__init__.py` TOOL_TO_COMMAND or `command_router` — the alias layer is untouched.

## Boundary-test discipline (read the retro)

This is the composition-risk task. Verify the FULL `pytest tests/`, not just per-task — the surface regression
tests (`test_adapter.py`, `test_command_router.py`) and session-end tests (`test_session_end.py`) span the swap.
Do not assert transient states (e.g. "adapter still holds a SessionStore").

## BDD Scenarios

- Requesting session status returns its lifecycle state and turn count
- Taking a turn on an ended session is refused
- Acting on a session owned by another learner is forbidden
- The tutor tool surface is unchanged after moving sessions onto the durable store
- Ending a session marks it ended and records the learner-state deltas
- A second device authenticated as the same learner resumes the same active session
