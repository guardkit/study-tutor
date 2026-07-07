# Reachy Local Voice Migration (FEAT-VOICE-004)

Migrate the Reachy Mini's voice conversation off the HF-cloud Realtime session onto a local
speech-to-speech unit on the GB10, with tutoring turns going **direct to the study-tutor**
(no Jarvis). Closes the D3 exception where a minor's voice transited a third-party cloud.

- **Review:** TASK-REV-RCH4
- **Spec:** `features/reachy-local-voice-migration/` (25 BDD scenarios)
- **Design:** `docs/design/voice-tutor-and-reachy-design.md` §7
- **Recon deltas:** `docs/research/ideas/reachy-local-backend-recon-deltas-2026-07-06.md`
- **Feature YAML:** `.guardkit/features/FEAT-VOICE-004.yaml` (traceability record)

## Execution model

**Not a study-tutor autobuild feature.** Code lands in the sibling `fleet-gateway` repo;
hardware work is operator-attended. Per build-plan §0a: **Operator + Opus**.

## Tasks (10) — see IMPLEMENTATION-GUIDE.md

- **Code plane (fleet-gateway):** R04 tool ABC shape · R05 Postgres read · R06 subject
  constant · R07 ask_tutor · R08 Scholar profile
- **Operator plane (live hardware):** R01 s2s standup · R02 Pi version · R03 re-point +
  round-trip · R09 clean re-clone deploy · SMK-R live smoke

## Waves

```
Wave 1: R01 · R02 · R04 · R06
Wave 2: R03 · R05 · R07
Wave 3: R08
Wave 4: R09
Wave 5: SMK-R
```

## Resolved decisions

**ASSUM-001 (subject) — resolved 2026-07-07: `english`.** The tutor is an English tutor
(persona, fine-tune, student model, `query_student_model` default all `english`); the app's
`maths` was a stale placeholder and has been moved to `english`. It is a subject-parameterized
**default**, so multi-subject is not constrained — full multi-subject needs only an app
subject picker + persona awareness later (plumbing already done). R06 is now reconcile-and-verify.

## Still open before build

Nothing blocking. All decision-assumptions are closed:

- **ASSUM-007 / ASSUM-008** — **resolved 2026-07-07**: Scholar persona copy (tutor-unavailable
  line + rotating "thinking" filler) drafted and recorded in R07 (tool offline string) + R08
  (persona copy). R08 wires it in.
- **ASSUM-003** — 0.6B vs 1.7B TTS checkpoint: **fallback pre-approved** (auto-accept 1.7B on
  the robot path if R-G2 fails); decided empirically at R01, no consult needed.
