---
id: TASK-VOX-003
title: "voice/utils.py \u2014 stdlib WebM/Ogg duration probe + synthetic audio builders\
  \ for tests"
task_type: feature
parent_review: TASK-REV-852B
feature_id: FEAT-VOICE-001
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
status: in_review
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-VOICE-001
  base_branch: main
  started_at: '2026-07-08T12:37:29.552380'
  last_updated: '2026-07-08T12:56:42.171559'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Coverage quality gate failed. Evidence bundle shows coverage_met:
      false while coverage_required: true, resulting in quality_gates.all_gates_passed:
      false. Evidence gathering status is ''partial_gate_abort'' (not ''complete''),
      and coverage metrics (line_coverage, branch_coverage, line_threshold, branch_threshold)
      are all null, indicating the coverage tool did not complete successfully.: Ensure
      code coverage tool runs successfully and that implementation achieves the required
      coverage thresholds. The evidence bundle''s gathering_status of ''partial_gate_abort''
      suggests evidence collection stopped at the coverage gate failure. Verify coverage
      configuration and re-run to capture complete coverage metrics.'
    timestamp: '2026-07-08T12:37:29.552380'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-07-08T12:47:47.263177'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Description

Port the LPA's stdlib duration probe (`lpa-platform-poc/src/voice/utils.py`)
verbatim-in-shape into `src/study_tutor/voice/utils.py`:

- `probe_duration_seconds(content: bytes, content_type: str) -> float | None`
  — dispatch on lowercased base MIME (strip `;codecs…`); `audio/webm` → EBML
  walk (first 64 KiB, magic check, unknown-size streamed Segment handled,
  `TimestampScale` default 1_000_000, 4/8-byte float Duration);
  `audio/ogg` → backwards `OggS` scan, page-structure validation, signed LE
  granule ≥ 0, `granule / 48_000`; anything else → `None`. **Never raises**
  on malformed input. m4a/MP4 returns `None` (byte cap + client stop govern —
  design §5.1; do not add an MP4 probe unless trivial).

- Test-support builders in `tests/unit/voice/audio_samples.py` (port of the
  LPA's `tests/voice/audio_samples.py`): `make_webm(duration_ticks, timescale_ns=None,
  streamed_segment=False)`, `make_ogg_page(granule, …)`, `make_ogg_opus(duration_seconds)`.
  These are consumed by TASK-VOX-004's boundary tests.

## Acceptance Criteria

- [ ] WebM with Duration element → correct seconds; Chrome-style streamed WebM (no Duration) → `None`
- [ ] Ogg/Opus EOS granule → `granule/48000`; header-page granule 0 → `None`; false-sync `OggS` bytes skipped
- [ ] Unknown/absent content types and truncated/garbage bytes → `None`, never an exception
- [ ] Builders produce bytes the probe itself parses (round-trip tests)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## References

- Design §5.1 (utils row) · `lpa-platform-poc/src/voice/utils.py` + `tests/voice/audio_samples.py` · blueprint §3
