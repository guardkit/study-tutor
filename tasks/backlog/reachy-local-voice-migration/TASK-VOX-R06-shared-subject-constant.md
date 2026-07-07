---
id: TASK-VOX-R06
title: "Reconcile the shared default subject to one source of truth"
task_type: declarative
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
repo: study-tutor
---

# Reconcile the shared default subject (recon D6 / ASSUM-001 — RESOLVED: english)

`resume_if_active` matches on `(student, subject)` (confirmed `session/service.py:218-233`).
Investigation resolved the D6 tension: the tutor is an **English** tutor (Scholar persona =
AQA English Lang 8700 / Lit 8702; `query_student_model` `DEFAULT_SUBJECT='english'`; the
fine-tune + student model are English Literature). The app's `defaultSubject = 'maths'` was
a stale v1 placeholder with no content behind it. Resolution: **`english` is the shared
default**; the app moves to match; fleet-gateway is already `english`.

This is a **default**, not a hard pin — the whole stack is already subject-parameterized, so
this does not constrain future multi-subject (see R07: `ask_tutor` takes `subject` as a
parameter and falls back to this default).

## Acceptance criteria

- **AC-R06-1**: The app's `defaultSubject` is `'english'` (`app/lib/ui/home_screen.dart`) —
  **DONE 2026-07-07**; the comment records it is the v1 default / future fallback.
- **AC-R06-2**: There is **one** documented source of truth for the v1 default subject
  string, and the app, the Scholar persona, and `query_student_model`'s default all resolve
  to the identical string (`english`).
- **AC-R06-3**: The default is discoverable by `ask_tutor` (R07) as its fallback value.
- **AC-R06-4**: All modified files pass project-configured lint/format checks with zero
  errors.

## Seam Tests

```python
"""Seam test: the tutoring default subject is identical across all consumers."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("SUBJECT_DEFAULT")
def test_subject_default_is_single_source():
    """All consumers must resolve to the same default subject string.

    Contract: one shared default subject; resume_if_active matches on (student, subject).
    Producer: TASK-VOX-R06
    """
    SHARED_DEFAULT_SUBJECT = "english"  # resolved value (ASSUM-001)
    # app defaultSubject (app/lib/ui/home_screen.dart) — assert equals SHARED_DEFAULT_SUBJECT
    # Scholar persona subject (AQA English) — assert consistent
    # query_student_model DEFAULT_SUBJECT — assert equals SHARED_DEFAULT_SUBJECT
    # ask_tutor fallback subject (R07) — assert equals SHARED_DEFAULT_SUBJECT
    assert SHARED_DEFAULT_SUBJECT == "english"
```

## Coach validation

- Grep the consumers for the default; assert identical (`english`); lint clean.

## Notes — multi-subject readiness

Pinning `english` as the **default** does not box out multiple subjects. The session store
keys on `(student, subject)`; `query_student_model` and `ask_tutor` both take a `subject`
parameter. Full multi-subject needs only (a) an app subject picker and (b) persona
multi-subject awareness — both out of v1 scope; the plumbing is already there.
