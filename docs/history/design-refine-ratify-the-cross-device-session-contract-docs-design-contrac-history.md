# /design-refine — ratify-the-cross-device-session-contract-docs-design-contrac — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /design-refine ratify-the-cross-device-session-contract-docs-design-contrac — 2026-07-03T21:49:16Z

### Prompt

```
/design-refine "Ratify the cross-device session contract (docs/design/contracts/API-session-cross-device.md §10) Proposed → Accepted: record the ADR-ARCH-008 partial supersession (HTTP/WS for app clients per ADR-FLEET-003), relax API-tutoring's end-once/append-only, and add the §9 SessionForbidden / Unauthenticated closed-set extension" \
  --context docs/design/contracts/API-session-cross-device.md \
  --context docs/design/contracts/API-tutoring.md \
  --context docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md \
  --context docs/handoffs/study-tutor-mobile-voice-conversation-starter.md
```

### Assistant response

I'll run the /design-refine session. First, let me check Graphiti availability and load the context files.

All context loaded. Before presenting the disambiguation, let me scan for downstream artefacts that reference the affected contracts (for the staleness phases) and check the C4 L3 diagram.

Approved — applying the three edits now. (Noted your message on the build-plan doc drift; I'll address it after the ratification completes.)

Contract ratified. Now the API-tutoring relaxation:

Now the ADR-ARCH-008 second partial supersession:

All three artefacts updated. Now running the staleness phases — let me check the authoritative W2 spec location you mentioned and the roadmap reference:
