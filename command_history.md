# Command History

Chronological record of slash-command invocations against the study-tutor repo.
First entry is the Phase 0 feature-plan run that produced FEAT-PO-002.

---

## 2026-04-20 — `/feature-plan FEAT-PO-002`

Invocation that produced the FEAT-PO-002 tutoring-runtime feature plan and
seven-task breakdown under `tasks/backlog/feat-po-002-tutoring-runtime/`.

```
/feature-plan FEAT-PO-002
```

Outputs:
- `tasks/backlog/feat-po-002-tutoring-runtime/README.md`
- `tasks/backlog/feat-po-002-tutoring-runtime/IMPLEMENTATION-GUIDE.md`
- `tasks/backlog/feat-po-002-tutoring-runtime/TASK-PO02-001` through `TASK-PO02-007`
- `.guardkit/features/FEAT-PO-002.yaml`
- Parent review: `tasks/in_review/TASK-REV-PO02-plan-feat-po-002-tutoring-runtime.md`


✅ Task Work Complete — TASK-PO02-003

  Intensity: LIGHT (auto-detected: feature subtask, complexity 4 ≤ 5)
  Stack: Python (study-tutor)

  Files changed

  - src/study_tutor/llm/client.py — new (84 LOC): LLMClient, _default_player_model(),
  LLMProviderError; Ollama HTTP via lazy httpx, Bedrock stub (NotImplementedError("…
  FEAT-PO-004")).
  - tests/unit/llm/test_provider_resolution.py — new (7 tests, includes the 2 seam tests from
  the task spec verbatim + 5 additional: unsupported-provider, HTTP call-shape, system omission,
   httpx error wrapping, no module-level instantiation).
  - tests/unit/llm/__init__.py — new.
  - pyproject.toml — added httpx>=0.27 to runtime deps; registered seam and integration_contract
   pytest markers.

  Quality gates

  - ✅ Tests: 7 / 7 passed
  - ✅ Coverage: 100% (32/32 stmts) on study_tutor.llm.client
  - ✅ SR-03 honoured: env read at call-time only; LLMClient never instantiated at module scope
  (asserted by test_no_module_level_client_instantiation).

  Notes / deviations

  - Spec text said OLLAMA_HOST; I used OLLAMA_BASE_URL to match the name TASK-PO02-001 actually
  established in .env.example. Default http://gb10.tailnet:11434 preserved. Model default
  gcse-tutor-gemma4-31b:Q4_K_M per spec — please confirm against the live GB10 tag.
  - Went direct to implementation under LIGHT intensity rather than spawning full
  planning/arch-review/code-review agent chain; this is a factory-shaped task with a clear
  reference pattern.

  State

  backlog → in_progress → in_review. Ready for your review, then /task-complete TASK-PO02-003.


✅ TASK-PO02-004 — Complete

  Workflow: MINIMAL (complexity 3, parent_review=TASK-REV-PO02)

  Files created:
  - src/study_tutor/session/tutor_session.py — TutorSession/TutorTurn dataclasses + SessionStore +
   module-level _store singleton
  - tests/unit/session/test_tutor_session.py — 5 tests
  - tests/unit/session/__init__.py

  Tests: 5/5 passing (0.01s)

  Contract adherence:
  - Plain dataclasses (Phase 1 Graphiti-friendly) ✓
  - Sync API, no I/O, no save()/to_json() ✓
  - end() flips status only — no Graphiti write ✓
  - UUID4 session IDs ✓
  - Injectable SessionStore (tests use their own instances) ✓

  State: BACKLOG → IN_REVIEW at
  tasks/in_review/feat-po-002-tutoring-runtime/TASK-PO02-004-tutor-session.md.

✻ Worked for 2m 16s

※ recap: Working on FEAT-PO-002 Phase 0 tutoring runtime; just finished TASK-PO02-004 (in-memory
  tutor session store with 5 passing tests), now in review. Next: run /task-complete TASK-PO02-004
   or pick up the next PO02 task. (disable recaps in /config)

   Task Work Complete — TASK-PO02-005

  Stack: Python (FastMCP + Click)
  Intensity: LIGHT (feature subtask, complexity 6)
  State: BACKLOG → IN_REVIEW

  Files created:
  - src/study_tutor/roles/loader.py — YAML manifest loader, paths resolved from Path.cwd()
  (SR-02 anchor)
  - src/study_tutor/mcp/adapter.py — MCPAdapter with 4 async handlers; _default_player_model()
  resolved per call (SR-03); asyncio.create_task warm-up on tutor_start_session
  - src/study_tutor/mcp/server.py — create_mcp_server() registers the 4 tools with
  SR-07-compliant descriptions
  - src/study_tutor/cli/main.py — click.group → serve subcommand; logging to stderr, banner via
  click.echo(err=True) (SR-01)
  - scripts/mcp-wrapper.sh — chmod +x; cd to absolute repo, sources .env, defaults
  AGENT_MODELS__REASONING_MODEL=local, exec's study-tutor serve
  - tests/unit/mcp/test_adapter.py — 6 smoke tests including SR-07 description check
  - README.md — claude_desktop_config.json snippet + SR-01/SR-02 rationale
  - pyproject.toml — entry point flipped to study_tutor.cli.main:cli (group)
  - .mcp.json — switched study-tutor entry to wrapper path

  Quality gates:
  - Tests: 18/18 pass (6 new + 12 existing)
  - SR-01 smoke: stdout 0 bytes after 2s serve; all output on stderr ✅
  - SR-02 smoke: wrapper invoked from /tmp — role.yaml resolved from abs repo root ✅
  - study-tutor serve --help exposes the expected flags
  - Server lists exactly 4 tools; tutor_session_end description = "Marks session ended." (no
  Graphiti leakage)

  Deferred to TASK-PO02-006: formal tests/unit/mcp/test_stdio_discipline.py parity suite.

✻ Cogitated for 6m 17s

※ recap: Goal: ship FEAT-PO-002 Phase-0 tutoring MCP runtime. Just finished TASK-PO02-005
  (adapter, CLI, bash wrapper) — 18/18 tests pass, task moved to in_review. Next: run
  /task-complete TASK-PO02-005, then start TASK-PO02-006 (stdio-discipline parity tests).
  (disable recaps in /config)


Task Work Complete — TASK-PO02-006

  State: backlog → in_progress → in_review

  Deliverables

  - tests/unit/mcp/test_stdio_discipline.py (new, 2 tests) — spawns real study-tutor serve with stdin
  closed, asserts zero stdout bytes in the 3-s startup window and banner lands on stderr (SR-01).
  - tests/unit/llm/test_provider_resolution.py — added
  test_adapter_handlers_do_not_reference_provider_string_literals: strips docstrings/comments from
  adapter.py then greps for provider literals (local, bedrock, openai, anthropic, gemini). Closes SR-03
  gap.
  - .claude/reviews/TASK-PO02-006-parity-log.md — full parity log with commands run, output captured,
  per-SR verdict, and final Six parity surfaces: GREEN line.

  Results

  - All 21 tests pass (.venv/bin/pytest tests/).
  - SR-01 & SR-03 code-verified; SR-02/04/06/07 shell-verified; SR-05 documented pass-through.
  - One minor AC-text adjustment documented in the log: SR-02's grep '^cd /' was written for an inline
  path; the wrapper uses the idiomatic REPO_ROOT="/…"; cd "$REPO_ROOT" pattern. The log verifies the same
   invariant with grep '^REPO_ROOT="/' + no-$PWD check.
  - No drift fixed in source tasks — prior tasks shipped the parity invariants correctly.