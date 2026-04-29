---
id: TASK-GSM-001
title: Define Pydantic entities and relationships for the student model
task_type: declarative
parent_review: TASK-REV-7DC0
feature_id: FEAT-1773
wave: 1
implementation_mode: direct
complexity: 3
estimated_minutes: 90
status: in_review
priority: high
created: 2026-04-27 00:00:00+00:00
updated: 2026-04-27 00:00:00+00:00
dependencies: []
tags:
- graphiti
- student-model
- schema
- pydantic
- declarative
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-1773
  base_branch: main
  started_at: '2026-04-29T16:11:30.550815'
  last_updated: '2026-04-29T16:17:57.291756'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-29T16:11:30.550815'
    player_summary: Created src/study_tutor/knowledge/student_model.py with the seven
      Pydantic v2 BaseModel entity classes (Student, Subject, Text, Topic, AssessmentObjective,
      Misconception, TopicConfidence), the six relationship-name string constants
      (STUDIES, WORKING_ON, HAS_TEXT, COVERS, ASSESSED_BY, HAS_CONFIDENCE), and the
      three group-id constants (STUDENT_GROUP_PREFIX='student:', SUBJECT_GROUP_PREFIX='subject:',
      FLEET_GROUP_ID='fleet:appmilla'). Added confidence_band_for(percentage:int)->str
      helper using a de
    player_success: true
    coach_success: true
---

# Task: Define Pydantic entities and relationships for the student model

## Description

Define the seven Pydantic entity types and six relationships that make up the student-model schema, plus the group-id format constants. This is the foundational data layer that all downstream slices in FEAT-1773 consume.

Per the build plan (Saturday afternoon, step 4) and `phase-1-scope.md §FEAT-PH1-001`, define entities exactly as the scope-doc tables specify — do not invent new types.

## Scope

**Entities** (`src/study_tutor/knowledge/student_model.py`):
- `Student` — identity, year_group, target_grade, created_at
- `Subject` — name, exam_board (e.g. AQA), spec_code (e.g. 8700)
- `Text` — name, type (`primary` / `secondary` / `context`), source_path
- `Topic` — name, subject_ref, ao_refs (list of AO codes)
- `AssessmentObjective` — code (AO1..AO6), description, exam_board
- `Misconception` — text, topic_ref, observed_at, confidence_band_at_observation
- `TopicConfidence` — student_ref, topic_ref, percentage (0–100), band (`struggling`/`developing`/`secure`/`mastered`), last_revised_at

**Relationships:**
- `Student STUDIES Subject`
- `Student WORKING_ON Text`
- `Subject HAS_TEXT Text`
- `Text COVERS Topic`
- `Topic ASSESSED_BY AssessmentObjective`
- `Student HAS_CONFIDENCE TopicConfidence` (carries percentage + band)

**Constants** (in same module):
- `STUDENT_GROUP_PREFIX = "student:"` — produces `student:<student_id>`
- `SUBJECT_GROUP_PREFIX = "subject:"` — produces `subject:<subject_slug>`
- `FLEET_GROUP_ID = "fleet:appmilla"` — fleet-wide knowledge scope

**Confidence-band thresholds** (per ASSUM-001, confirmed):
- `0–39`: struggling
- `40–69`: developing
- `70–89`: secure
- `90–100`: mastered

## Acceptance Criteria

- [ ] Seven entity classes defined as `pydantic.BaseModel` subclasses with field types matching scope-doc tables
- [ ] Six relationship constants defined as string literals (`STUDIES`, `WORKING_ON`, `HAS_TEXT`, `COVERS`, `ASSESSED_BY`, `HAS_CONFIDENCE`)
- [ ] Three group-id constants (`STUDENT_GROUP_PREFIX`, `SUBJECT_GROUP_PREFIX`, `FLEET_GROUP_ID`) exposed as module-level constants
- [ ] `confidence_band_for(percentage: int) -> str` helper returns the correct band per ASSUM-001 thresholds
- [ ] Module docstring documents the cross-repo divergence: study-tutor uses `fleet:appmilla` per phase-1-scope.md (specialist-agent uses `appmilla-fleet` — see ASSUM-008)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit tests in `tests/unit/knowledge/test_student_model.py`:
  - Each entity validates required fields (rejects partial input)
  - `confidence_band_for(0..100)` returns correct band at each boundary
  - Group-id constant values match the scope-doc convention
  - Pydantic schema dump matches an expected JSON shape

## Implementation Notes

- This is a **declarative** task — pure type definitions, no behaviour, no async, no I/O
- Follow `agentic-dataset-factory` Pydantic patterns where applicable
- Do NOT import graphiti-core here; entity types are stack-agnostic
- Constants are imported by every downstream slice — keep them stable

## §4 Integration Contract Producer

This task produces three contracts consumed by downstream slices:

1. **PydanticEntities** — exported types (`Student`, `Subject`, `Text`, `Topic`, `AssessmentObjective`, `Misconception`, `TopicConfidence`)
2. **GroupIdConstants** — `STUDENT_GROUP_PREFIX`, `SUBJECT_GROUP_PREFIX`, `FLEET_GROUP_ID`
3. **ConfidenceBandThresholds** — `confidence_band_for(int) -> str`

See `IMPLEMENTATION-GUIDE.md §4` for full contract specifications.
