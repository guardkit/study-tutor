# FEAT-VOICE-001 — server voice module (W1 of the voice build plan)

Non-streaming `voice_turn` + `voice_audio` behind `STUDY_TUTOR_VOICE_ENABLED`,
porting the proven lpa-platform-poc voice shape onto Starlette idioms.

- **Plan:** [voice scope & build plan](../../../docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md) §5 W1
- **Guide:** [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) (diagrams + §4 contracts — read first)
- **Spec:** [features/voice-server-module/](../../../features/voice-server-module/voice-server-module_summary.md)
- **Order (sequential):** VOX-001 → VOX-003 → VOX-002 → VOX-004 → VOX-005 → VOX-006 → VOX-007
- **W1 exit gate (plan §5):** full tutor suite green; seam tests pin the wire; flag off ⇒ 404.

| Task | What | cx | mode |
|---|---|---|---|
| TASK-VOX-001 | config + six errors | 3 | direct |
| TASK-VOX-003 | duration probe + builders | 4 | task-work |
| TASK-VOX-002 | AudioClient + wire pins | 5 | task-work |
| TASK-VOX-004 | in-memory multipart validation | 6 | task-work |
| TASK-VOX-005 | service + chunk store (ASSUM-005) | 6 | task-work |
| TASK-VOX-006 | routes + flag + wiring | 6 | task-work |
| TASK-VOX-007 | BDD step definitions | 5 | task-work |
