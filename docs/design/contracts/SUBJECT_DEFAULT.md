# Contract — SUBJECT_DEFAULT (shared default tutoring subject)

**Contract name:** `SUBJECT_DEFAULT` (seam marker: `integration_contract("SUBJECT_DEFAULT")`)
**Producer task:** TASK-VOX-R06 (FEAT-VOICE-004 — Reachy local voice migration)
**Consumer tasks:** TASK-VOX-R07 (`ask_tutor` fallback), TASK-VOX-R08 (Scholar persona)
**Resolved value:** `english` — ASSUM-001, resolved 2026-07-07
**Status:** Active. This is a **v1 default, not an immutable pin** — multi-subject stays open.

---

## 1. The one value

```
SUBJECT_DEFAULT = "english"
```

There is exactly **one** default tutoring subject string for v1, and every consumer
below MUST resolve to it verbatim. This document is that single source of truth.

## 2. Why it must be single-sourced

The study-tutor session store's `resume_if_active` matches on **`(student, subject)`**,
not on `student` alone (`src/study_tutor/session/service.py`). If any consumer talks to
the tutor with a *different* subject string, it silently creates a **parallel session**
and defeats **D8 cross-device pickup** (a session started on the phone, resumed on the
Reachy robot). Divergence is therefore not a cosmetic bug — it breaks the headline
feature by construction. Pinning one shared default makes that divergence impossible.

## 3. Consumers (all resolve to `english`)

| Consumer | Location | How it uses the default |
|---|---|---|
| Flutter app `defaultSubject` | study-tutor `app/lib/ui/home_screen.dart` | The subject sent on `startSession` until an app subject picker lands (v1 has none). |
| fleet-gateway `DEFAULT_SUBJECT` | fleet-gateway `common/subject.py` | Single source for the robot-side consumers below. |
| `query_student_model` | fleet-gateway `reachy…/external_tools.py` | Progress-read default subject. |
| `ask_tutor` fallback | fleet-gateway `reachy…/external_tools.py` (TASK-VOX-R07) | The subject sent on `POST /api/sessions/start` when the persona omits it — **never empty**. |
| Scholar persona | fleet-gateway `reachy/external_content/external_profiles/scholar/` | AQA English Language (8700) / Literature (8702); "leave the subject unset (it defaults to English)". |

The tutor is an **English** tutor end to end — the persona, the fine-tune, the student
model, and this default all agree. The app's former `'maths'` was a stale placeholder
with no content behind it; it was reconciled to `'english'` on 2026-07-07 (ASSUM-001).

## 4. Default, not a pin — multi-subject stays open

Pinning `english` as the **default** does not constrain future multi-subject. The whole
stack is already subject-parameterised:

- the session store keys on `(student, subject)`;
- `query_student_model` and `ask_tutor` both take a `subject` parameter.

Full multi-subject needs only (a) an app subject picker and (b) persona multi-subject
awareness — both out of v1 scope. When a picker lands, `defaultSubject` becomes the
*fallback* rather than a fixed value; no rework of the seam is required.

## 5. Validation

The seam test `test_subject_default_is_single_source`
(`tests/seam/test_subject_default.py`, markers `seam` + `integration_contract("SUBJECT_DEFAULT")`)
mechanically asserts the app's `home_screen.dart` declares `defaultSubject = 'english'`,
and — when the sibling fleet-gateway checkout is present — that
`common/subject.py`'s `DEFAULT_SUBJECT == "english"` and the Scholar persona is
consistent (English, not maths). The sibling legs skip cleanly when fleet-gateway is
absent so the hermetic run stays green anywhere. `ask_tutor`'s non-empty-fallback and
verbatim-forward behaviour is validated by its own seam test in fleet-gateway (R07).
