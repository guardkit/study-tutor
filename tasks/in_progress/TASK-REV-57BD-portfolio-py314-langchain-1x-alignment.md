---
id: TASK-REV-57BD
title: Verify Python 3.14 + langchain-1.x portfolio alignment (per Jarvis FEAT-J004-702C precedent)
status: review_complete
task_type: review
review_mode: diagnostic
review_depth: standard
created: 2026-04-28T00:00:00Z
updated: 2026-04-29T00:00:00Z
previous_state: in_progress
state_transition_reason: "Diagnostic review complete; awaiting [A]/[I]/[R]/[C] decision"
priority: high
tags: [portfolio-alignment, langchain-1x, python-pinning, FA04-followup, ddd-southwest-demo]
complexity: 0
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-29T00:00:00Z
review_results:
  mode: diagnostic
  depth: standard
  score: 92
  findings_count: 7
  recommendations_count: 5
  decision: implement
  decided_at: 2026-04-29T00:00:00Z
  report_path: .claude/reviews/TASK-REV-57BD-report.md
  implementation_feature:
    feature_id: FEAT-7BDP
    feature_slug: py314-langchain-pin-alignment
    folder: tasks/backlog/py314-langchain-pin-alignment/
    subtasks: [TASK-PLA-001, TASK-PLA-002, TASK-PLA-003]
    waves: 1
    deferred_promoted: [TASK-IMP-B7E0]  # R5 deepagents drift — promoted to backlog task 2026-04-29 (was: R5-deepagents-adr-drift deferred to Phase 1)
  empirical_evidence:
    python_version: "3.14.2"
    install_outcome: "success (uv pip install -e \".[dev,providers]\")"
    pytest_outcome: "23/23 passed in 6.84s"
    langchain_runtime_failures: 0
    resolved_versions:
      langchain: "1.2.15"
      langchain-core: "1.3.2"
      langchain-openai: "1.2.1"
      langchain-anthropic: "1.4.2"
      langchain-google-genai: "4.2.2"
      langchain-aws: "1.4.5"
      langchain-ollama: "1.1.0"
      langgraph: "1.1.10 (transitive)"
related_external_reviews:
  - "guardkit/.claude/reviews/TASK-REV-FA04-report.md"  # langchain trapdoor diagnosis (closed)
  - "jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md"  # rev2 pin recipe
  - "guardkit/docs/guides/portfolio-python-pinning.md"  # portfolio policy
---

# Verify Python 3.14 + langchain-1.x portfolio alignment (per Jarvis FEAT-J004-702C precedent)

## Context

Jarvis hit a 33-min autobuild stall on FEAT-J004-702C run 1 (2026-04-27) caused by a stale Python pin (`>=3.12,<3.13`) excluding Mac's default Python 3.14, compounded by langchain ecosystem 0.x→1.x version skew when the resolver was given open-floor `>=0.3` pins. Investigation: [`guardkit/.claude/reviews/TASK-REV-FA04-report.md`](../../../guardkit/.claude/reviews/TASK-REV-FA04-report.md). Remediation in Jarvis: [`jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`](../../../jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md) Revision 2 — `requires-python = ">=3.11"` + langchain ecosystem coherent 1.x with `<2` caps. Empirical Jarvis run 2 validation: 12 tasks completed cleanly on the new recipe.

The portfolio rollout was paused while orchestrator-side issues (CEIL/WALL/FRSH/FLOR) were resolved. With Jarvis now stable end-to-end, this review picks up the rollout for study-tutor.

**study-tutor is DDD South West demo-critical** (per `guardkit/tasks/backlog/autobuild-stall-resilience/README.md`: "Autobuild builds jarvis/study-tutor/forge for the demo"). This review is **high priority** — but the risk profile here is *lighter* than forge or specialist-agent because study-tutor's pins are already partially coherent (langchain and langchain-core both on 1.x).

## Current pin state (read directly from `pyproject.toml` — pre-review snapshot)

```toml
requires-python = ">=3.11"

dependencies = [
    "pydantic>=2.0,<3.0",
    "langchain>=1.2.11",          # 1.x ✓
    "langchain-core>=1.2.18",     # 1.x ✓
    # NOTE: langgraph not listed as direct dep — study-tutor uses langchain
    # for LLM client, not the graph orchestration framework. This is a
    # different shape from forge/specialist-agent/jarvis (DeepAgents-based)
    # and likely lower-risk for the langgraph-mismatch class.
    ...
]

[project.optional-dependencies]
providers = [
    "langchain-openai",            # unpinned floor — RISK
    "langchain-anthropic",         # unpinned floor — RISK
    "langchain-google-genai",      # unpinned floor — RISK
    "langchain-aws",               # unpinned floor — RISK
    "langchain-ollama",            # unpinned floor — RISK
]
```

**Observation**: study-tutor's runtime pins are coherent (1.x) but the providers are *completely unpinned*. The resolver will pick "the latest compatible at install time" — which today happens to work but offers zero protection against the next breaking-change wave. This is exactly the structural problem ADR-ARCH-010-rev2 solved by adding `<2` caps.

study-tutor *also* doesn't depend on `deepagents` or `langgraph` — it's the lightest-weight LangChain consumer in the portfolio. That changes which Jarvis-precedent failures apply to it (the langgraph 0.x mismatch obviously can't bite here) and which don't.

## Goal

Apply the relevant subset of the FA04 recipe to study-tutor:
1. Empirically confirm that the current state works on Python 3.14.
2. Add `<2` caps to the provider pins for forward protection.
3. Optionally add explicit lower-bound floors to the providers (matching the Jarvis-verified-on-3.14 set: `langchain-anthropic>=1.4,<2`, `langchain-openai>=1.2,<2`, `langchain-google-genai>=4.2,<5`).
4. Capture the change as a study-tutor-side ADR.

**No GuardKit changes; no Jarvis changes — fixes live in this repo.**

## Source artefacts

- This repo: `pyproject.toml`, `uv.lock` (if present), `tests/`, `docs/architecture/decisions/`
- Empirical Jarvis run-2 evidence: `jarvis/docs/history/autobuild-FEAT-J004-702C-run-2-history.md` (Waves 1-4 baseline)
- Jarvis ADR rev2: `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`
- Portfolio guide: `guardkit/docs/guides/portfolio-python-pinning.md`

## Investigation scope

1. **Empirical 3.14 install + test run** (focal: do unpinned providers resolve cleanly today?):
   ```bash
   cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor
   mv .python-version .python-version.bak 2>/dev/null
   rm -rf .venv
   uv venv --python 3.14 .venv
   uv pip install --upgrade --python .venv/bin/python -e ".[dev,providers]"
   .venv/bin/python -m pytest --tb=no -q | tee /tmp/study-tutor-3.14-pytest.log
   mv .python-version.bak .python-version 2>/dev/null
   ```

2. **Capture resolved provider versions** — these are the floors we'd pin to. Critical question: do they match Jarvis's verified-on-3.14 set, or has the ecosystem moved further?

3. **Failure categorisation** — same playbook as FA04. Expected: small failure count (study-tutor's runtime pins are already 1.x), maybe just `langchain-aws` / `langchain-ollama` API drift if any.

4. **Provider-pin recommendation**:
   - Default: lift the unpinned providers to explicit floors `>=X.Y,<2` based on resolved versions.
   - Alternative if the ecosystem shifted: pin to whatever resolved-clean today's versions are.
   - Document why study-tutor doesn't need `deepagents` / `langgraph` pins (so future readers understand the omission is deliberate).

5. **ADR**: file as the next available `ADR-ARCH-XXX` referencing ADR-ARCH-010-rev2 as the cross-repo precedent.

6. **Confirm langgraph-absence is intentional**: grep the codebase for any `langgraph` import. If present (perhaps via a transitive path), it should be pinned. If genuinely absent, document the rationale in the ADR.

## Acceptance criteria

- [ ] Empirical 3.14 + `uv pip install --upgrade -e ".[dev,providers]"` succeeds and `.venv/bin/python -c "import study_tutor"` (or the package's actual import name) works.
- [ ] Full pytest run captured.
- [ ] Resolved versions table for all `langchain-*` packages documented.
- [ ] Failure categorisation: each failing test sorted (pin guard / langchain runtime / API-level break / pre-existing).
- [ ] Provider-pin recommendation: explicit diff against current `pyproject.toml` adding `<2` caps and lower-bound floors to currently-unpinned providers.
- [ ] Confirmation that `langgraph` is not used in the codebase (grep evidence) OR a recommendation to add it as an explicit pin if used transitively.
- [ ] New ADR drafted with rationale, verified-versions table, cross-repo precedent reference, and explanation of why study-tutor doesn't need `deepagents`/`langgraph` pins.
- [ ] Recommendation on whether study-tutor needs portfolio-pinning guide reference in its `CLAUDE.md`.
- [ ] No proposed changes to GuardKit or Jarvis — fixes live in this repo.
- [ ] Report saved to `.claude/reviews/TASK-REV-57BD-report.md`.

## Out of scope

- Implementing the pin updates — follow-up via `/task-review` → [I]mplement.
- Investigating the orchestrator complexity/timeout family (closed by 9D13 + CEIL/WALL/FRSH/MAXT/FLOR).
- Adding `deepagents` or `langgraph` if study-tutor genuinely doesn't need them — preserve the lightweight footprint.
- Other portfolio repos — each has its own review task in its own `tasks/backlog/`.

## Suggested workflow

```bash
/task-review TASK-REV-57BD --mode=diagnostic
# Run the empirical 3.14 install + pytest.
# Confirm langgraph-absence is intentional.
# Compare resolved provider versions against Jarvis's verified-on-3.14 set.
# Draft the pin diff and the ADR.
# Surface the [A]ccept / [I]mplement / [R]evise checkpoint.
```

## References

- Cross-repo (read-only): `guardkit/.claude/reviews/TASK-REV-FA04-report.md`
- Cross-repo (read-only): `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md` Revision 2
- Cross-repo (read-only): `guardkit/docs/guides/portfolio-python-pinning.md`
- This repo: `pyproject.toml`, `tests/`, `docs/architecture/decisions/`
