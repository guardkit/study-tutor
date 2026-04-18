# ADR-ARCH-010 — Pydantic-at-boundary validation + domain vocabulary enums

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-001, ADR-ARCH-012 (deepagents 0.5.3 structured output)

## Context

Study Tutor has several boundary surfaces where untyped dict-style
payloads cross contexts:

- MCP tool inputs (`tutor_start_session`, `tutor_turn`, etc.).
- LLM client invocations (messages, options).
- Graphiti entity write-back (Phase 1+).
- Session-export JSON (Phase 1+ schema, Phase 2 consumer).

Without a validation discipline, each boundary risks silent type
drift. LES1's evidence base (e.g. TASK-MDF-POLR) shows that
tool-description ↔ handler-signature drift is a load-bearing
failure mode.

deepagents 0.5.3 specifically added "static structured output for
subagent responses" — reinforcing Pydantic as the blessed schema
path.

## Decision

**Every boundary validates with Pydantic.**

| Boundary | Schema model |
|---|---|
| MCP tool input | `TutorStartSessionRequest`, `TutorTurnRequest`, `TutorSessionStatusRequest`, `TutorSessionEndRequest` |
| MCP tool output | `TutorSessionHandle`, `TutorTurnResponse`, `TutorSessionStatusResponse` |
| LLM client invoke | `LLMInvokeOptions` |
| Graphiti entities (P1+) | `Student`, `TopicConfidence`, `Misconception`, `SessionEpisode`, `AssessmentObjectiveProgress` |
| Coach output (P1+) | `TurnFeedback`, `SessionSummary` (with Pydantic `structured_output=`) |
| Session export (P1+) | `SessionExport` (full schema) |
| Gamification events | `SessionCompletedEvent`, `AchievementUnlockedEvent`, etc. |

**Domain vocabulary** lives in a shared-kernel Python module
(`src/study_tutor/domain/taxonomy.py` — Phase 1):

- `Subject` (English Language / English Literature)
- `Paper` (Paper 1 / Paper 2)
- `AssessmentObjective` (AO1–AO6)
- `GradeTarget` (4–9)
- `ConfidenceBand` (Struggling / Developing / Secure / Mastered)
- `SessionState` (initialised / planning / active / summarising / ended)

These enums are imported by Tutoring, Knowledge, Student Model, and
Gamification contexts (shared kernel per ADR-ARCH-001).

## Alternatives considered

- **TypedDict / dataclass.** Rejected. TypedDict gives no runtime
  validation; dataclass gives basic validation but not the ergonomic
  `.model_validate()` / `.model_dump_json()` surface.
- **Marshmallow / attrs.** Rejected. LangChain + deepagents both use
  Pydantic natively — one schema library is cleaner.
- **Protobuf / Avro.** Rejected. Overkill for single-language single-user
  system; adds compile step.

## Consequences

**Positive:**
- Every boundary has a declarative schema that serves as documentation
  and runtime validation simultaneously.
- Matches deepagents 0.5.3 structured-output pattern.
- Domain enums prevent stringly-typed bugs (e.g. `"AO1"` vs `"ao1"`).

**Negative:**
- Schema churn early in Phase 1 (Student Model design settling).
  Mitigated by versioning entities and using `model_config =
  ConfigDict(extra='allow')` where forward-compatibility matters.
- Slight per-call overhead for model validation. Negligible vs LLM
  inference cost.

## References

- deepagents 0.5.3 release notes (static structured output for
  subagents).
- `domain-model.md §8.1` for the full shared-kernel taxonomy.
