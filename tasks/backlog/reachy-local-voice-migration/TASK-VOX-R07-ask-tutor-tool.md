---
id: TASK-VOX-R07
title: "Implement the ask_tutor external tool (direct to study-tutor)"
task_type: feature
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 2
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VOX-R06]
repo: fleet-gateway
consumer_context:
  - task: TASK-VOX-R06
    consumes: SUBJECT_DEFAULT
    framework: "ask_tutor tool (subject parameter with default)"
    driver: "static string fallback"
    format_note: "Exposes subject as a tool parameter (persona-supplied for multi-subject); falls back to the shared default 'english' when omitted. NEVER sends empty — resume_if_active matches on (student, subject), so an empty subject would create a parallel session and defeat D8 pickup (recon D6)."
  - task: TASK-APP-001
    consumes: STUDY_TUTOR_HTTP_8100
    framework: "httpx (connect-per-call, bearer)"
    driver: "httpx"
    format_note: "POST /api/sessions/start then POST .../turn on the study-tutor adapter :8100; same binding the app consumes"
---

# Implement the ask_tutor external tool (design §7.4)

New external tool cloned from `ask_jarvis`'s plumbing, pointed at the study-tutor HTTP
adapter — giving the robot **identical session semantics to the phone**, which is what makes
D8 cross-device pickup real. No Jarvis in the tutoring loop.

## Acceptance criteria

- **AC-R07-1**: `ask_tutor` conforms to the Pollen `core_tools.Tool` ABC
  (`parameters_schema` + async `__call__`), connect-per-call, generous timeout.
- **AC-R07-2**: First call ensures a session via `POST /api/sessions/start` with
  `resume_if_active: true`; subsequent calls `POST …/turn`; returns `tutor_response` text to
  the Realtime session.
- **AC-R07-3**: `subject` is a **tool parameter** (persona-supplied, enabling multi-subject);
  when the persona omits it, it **falls back to the shared default `english`** (R06). It is
  **never sent empty** — an omitted/empty subject defaults server-side to `""`, creating a
  parallel session and defeating D8 pickup (recon D6).
- **AC-R07-4**: On study-tutor unavailability (httpx error / non-2xx / **rejected bearer**),
  the tool returns the **same** neutral offline string — `"The tutor isn't reachable right
  now."` — for every failure mode, so no network/auth/status detail can reach the Realtime
  session. It never raises; the persona renders this warmly (R08, ASSUM-007). Because auth
  failures collapse to the identical string, the credential failure cannot be spoken as
  tutoring content by construction.
- **AC-R07-5**: Transport is HTTP to `http://promaxgb10-41b1:8100`, bearer token, same
  binding the app consumes.
- **AC-R07-6**: All modified files pass project-configured lint/format checks with zero
  errors.

## Seam Tests

```python
"""Seam test: ask_tutor sends resume_if_active + a non-empty subject over :8100."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("SUBJECT_DEFAULT")
def test_ask_tutor_sends_subject_default_and_resume():
    """ask_tutor sends resume_if_active=true and a non-empty subject (default english).

    Contract: subject falls back to the R06 shared default when the persona omits it;
    never empty. Producer: TASK-VOX-R06
    """
    SHARED_DEFAULT_SUBJECT = "english"  # from R06 (ASSUM-001)
    # Inject httpx MockTransport; drive one call WITHOUT a subject arg; assert the /start
    # body carries resume_if_active=true and subject==SHARED_DEFAULT_SUBJECT (not "").
    # Drive a second call WITH subject="literature"; assert it is forwarded verbatim
    # (multi-subject path). Assert a non-2xx yields the graceful offline string, not a raise.
    pass
```

## Coach validation

- MockTransport seam tests green (default fallback is non-empty + forwarded-subject +
  resume flag + graceful-offline mapping); ABC conformance asserted; lint clean.

## Notes

- Latency honesty: a tutor turn is ~5 s+; the persona covers the gap conversationally
  (R08). `ask_tutor` is for tutoring turns only; simple chat stays on the s2s LLM stage.
- `ask_jarvis` stays installed for non-tutoring fleet queries.
- Multi-subject: the `subject` parameter is the seam that carries any subject once the app
  gains a picker and the persona learns to pass it — no rework here.
