# Review Report: TASK-REV-57BD — Python 3.14 + langchain-1.x portfolio alignment (study-tutor)

**Mode**: Diagnostic
**Depth**: Standard
**Subject**: Confirm study-tutor's pinning posture against the FA04/ADR-ARCH-010-rev2 portfolio precedent
**Date**: 2026-04-29
**Constraint**: DDD South West demo (autobuild builds jarvis/study-tutor/forge for the demo)

**Source artefacts read**:
- This repo: `pyproject.toml`, `uv.lock`, `tests/`, `docs/architecture/decisions/ADR-ARCH-{004,012}-*.md`
- Cross-repo (read-only): `guardkit/.claude/reviews/TASK-REV-FA04-report.md`
- Cross-repo (read-only): `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md` (rev2)
- Cross-repo (read-only): `guardkit/docs/guides/portfolio-python-pinning.md`
- Empirical artefacts (this run, fresh 3.14 venv):
  - `/tmp/study-tutor-3.14-install.log`
  - `/tmp/study-tutor-3.14-pip-list.txt`
  - `/tmp/study-tutor-3.14-pytest.log`

---

## Executive Summary

study-tutor is **already largely aligned** with ADR-ARCH-010-rev2's portfolio recipe. A clean Python 3.14.2 venv with `uv pip install -e ".[dev,providers]"` resolves cleanly and the full test suite passes (**23/23 in 6.84s**). The unpinned `[providers]` extras resolve today to **the exact same set Jarvis verified on 3.14**, with one provider one patch ahead (`langchain-anthropic 1.4.2` vs Jarvis's 1.4.1).

The remaining gap is **forward protection**: study-tutor's `[providers]` extras are completely unpinned (`langchain-openai`, `langchain-anthropic`, `langchain-google-genai`, `langchain-aws`, `langchain-ollama`). Today the resolver picks coherent 1.x for all of them; the next time the ecosystem ships a 2.x major (or a 0.x→1.x-style breaking change), the same trapdoor that bit Jarvis on FA04 opens here. The fix is a four-line diff: add `<2` (or `<5` for `langchain-google-genai`) caps and explicit lower-bound floors matching today's resolved versions.

There are **no langchain-runtime failures**, **no langgraph imports** in source (transitive only via `langchain`), and **no `deepagents` usage** in source — even though `ADR-ARCH-004` and `ADR-ARCH-012` declare `deepagents>=0.5.3` as part of the planned Phase 1 stack. That ADR/pyproject discrepancy is a separate finding (§6) and is **out of scope for this review's pin update** — it just needs to be acknowledged so the new ADR's "study-tutor doesn't need deepagents pins" rationale is auditable.

**Risk profile**: lighter than Jarvis or specialist-agent. study-tutor's runtime pins are already 1.x-coherent, and the Phase 0 codebase doesn't yet import the planned Phase 1 stack components (deepagents, AsyncSubAgent, CompositeBackend). The pin alignment is a forward-protection change, not an incident remediation.

---

## 1. Empirical evidence

### 1.1 Install

```bash
$ cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor
$ rm -rf .venv && uv venv --python 3.14 .venv
Using CPython 3.14.2 interpreter at: /usr/local/bin/python3.14
Creating virtual environment at: .venv

$ uv pip install --upgrade --python .venv/bin/python -e ".[dev,providers]"
# (truncated; exit code 0 — all packages resolved cleanly, including
#  the five unpinned providers)

$ .venv/bin/python -c "import study_tutor; print('OK')"
OK
```

No `.python-version` file existed in the repo (verified: `ls -la .python-version*` → no matches), so no temporary backup was needed. The pre-existing `.venv` was Python 3.11.14 (created by an earlier `uv venv` invocation without an explicit `--python`); the test venv is now 3.14.2. **No source-controlled file in the repo was modified by this review** — only the local `.venv` directory was rebuilt.

### 1.2 pytest

```
$ .venv/bin/python -m pytest --tb=short -q
.......................                                                  [100%]
23 passed in 6.84s
```

**Zero failures, zero langchain-runtime errors.** Categorisation per FA04 playbook:

| Category | Count | Notes |
|----------|-------|-------|
| Pin-tracking guard test failures (rebase needed) | 0 | study-tutor doesn't currently have explicit pin-guard tests like Jarvis's `test_phase2_dependencies.py` — see §7 recommendation |
| `langchain` runtime failures | 0 | None |
| API-level breaks | 0 | None |
| Pre-existing failures (docstring drift, infra fragility) | 0 | None |
| **Total failing tests** | **0/23** | |

This is materially cleaner than Jarvis on rev2 (`7 failures, of which 0 are langchain-runtime` — 25→7 after the rev2 pins were applied). study-tutor starts from a cleaner baseline because its runtime pins were already coherent 1.x; the only resolver freedom was in the providers, and today the resolver happens to pick coherent 1.x there too.

### 1.3 Resolved provider versions (Python 3.14.2 venv, fresh install, 2026-04-29)

| Package | Resolved | Pin in `pyproject.toml` | Jarvis verified-on-3.14 (rev2) | Match |
|---|---|---|---|---|
| `langchain` | **1.2.15** | `>=1.2.11` | 1.2.15 | ✓ exact |
| `langchain-core` | **1.3.2** | `>=1.2.18` | 1.3.2 | ✓ exact |
| `langchain-openai` | **1.2.1** | *(no floor, no cap)* | 1.2.1 | ✓ exact |
| `langchain-anthropic` | **1.4.2** | *(no floor, no cap)* | 1.4.1 | one patch ahead |
| `langchain-google-genai` | **4.2.2** | *(no floor, no cap)* | 4.2.2 | ✓ exact |
| `langchain-aws` | **1.4.5** | *(no floor, no cap)* | *(not in Jarvis set)* | new |
| `langchain-ollama` | **1.1.0** | *(no floor, no cap)* | *(not in Jarvis set)* | new |
| `langgraph` (transitive) | **1.1.10** | *(not declared)* | 1.1.10 | ✓ exact |
| `langgraph-checkpoint` | 4.0.3 | *(transitive)* | — | — |
| `langgraph-prebuilt` | 1.0.12 | *(transitive)* | — | — |
| `langgraph-sdk` | 0.3.13 | *(transitive)* | — | — |
| `pydantic` | 2.13.3 | `>=2.0,<3.0` | — | — |
| `mcp` | 1.27.0 | `>=1.0` | — | — |

**Reading**: Today's resolver picks the same 1.x coordinated set Jarvis verified, including for the two providers Jarvis doesn't declare (`langchain-aws`, `langchain-ollama`). This is the **best possible state for converting unpinned providers to explicit floors**: we know empirically that those exact versions install cleanly and run the test suite green on the same Python the demo machine has on PATH.

---

## 2. langgraph absence — confirmed intentional

```bash
$ grep -rn "import langgraph\|from langgraph" --include="*.py" .
# (no matches)
```

`langgraph` is present in `uv.lock` only as a transitive dependency of `langchain` (verified at `uv.lock:725-733`: `langchain` → `langgraph`). study-tutor doesn't declare it, doesn't import it, and doesn't depend on its API directly.

**Recommendation**: do **not** add `langgraph>=1.1,<2` as a direct dep in study-tutor. It would create a maintenance obligation (every future bump needs revalidation here) for zero protection benefit — `langchain>=1.2,<2` already implies `langgraph<2` via the transitive constraint. The new ADR (§5) should explicitly record this rationale so a future reader looking at Jarvis's pin and wondering why study-tutor diverges has the answer.

This is the canonical "the same recipe doesn't apply identically across the portfolio" pattern. study-tutor is genuinely a lighter LangChain consumer than Jarvis; the pin set should reflect that.

---

## 3. deepagents absence — confirmed in code, but inconsistent with ADRs

```bash
$ grep -rn "import deepagents\|from deepagents" --include="*.py" .
# (no matches)

$ grep -n "deepagents" pyproject.toml
# (no matches)
```

The current `pyproject.toml` has **no** `deepagents` declaration in either the runtime deps or the `[providers]` extra. No source file imports it.

**However**, two existing ADRs declare `deepagents>=0.5.3` as part of the planned stack:

- `ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md` lists `deepagents >= 0.5.3` in the framework table with annotation "Declared in `[providers]` extra".
- `ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md` decision text: "Pin `deepagents >= 0.5.3` in `pyproject.toml` `[providers]` extra (CC-04) from Phase 0 for SR-04 smoke-test compliance, even though Phase 0 code does not import deepagents yet."

This is a **pre-existing drift between ADR and codebase** — orthogonal to the FA04/3.14 alignment review, but discovered during it. Two interpretations:

1. **The ADRs are aspirational and Phase 1 will add the dep.** In that case, when deepagents gets added it should be pinned coherently with the Jarvis recipe: `deepagents>=0.5.3,<0.6`. This review's pin diff (§4) deliberately doesn't add it — adding deepagents now without a Phase 1 import to validate it against would just defer the same audit a few weeks. The new ADR (§5) should call this out as "deferred until Phase 1 begins importing AsyncSubAgent".
2. **The Phase 1 architecture has changed and the ADRs need updating.** This is a separate decision the review can't make on the user's behalf. Flag it for follow-up.

**Recommendation**: out of scope to resolve here. Note the discrepancy in the new ADR and let Phase 1 implementation work pick it up. The pin alignment doesn't depend on resolving it.

---

## 4. Recommended pin diff

The minimal, behaviour-preserving forward-protection change. Floors match today's resolved versions; caps match the FA04 recipe.

```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -8,8 +8,15 @@ description = "Fine-tuned English tutoring runtime (MCP adapter + LLM client) f
 requires-python = ">=3.11"
 license = {text = "MIT"}
 dependencies = [
     "pydantic>=2.0,<3.0",
     "pyyaml>=6.0",
     "click>=8.0",
-    "langchain>=1.2.11",
-    "langchain-core>=1.2.18",
+    "langchain>=1.2.11,<2",
+    "langchain-core>=1.2.18,<2",
     "python-dotenv>=1.0",
     "mcp>=1.0",
     "httpx>=0.27",
@@ -23,11 +25,15 @@ study-tutor = "study_tutor.cli.main:cli"

 [project.optional-dependencies]
 providers = [
-    "langchain-openai",
-    "langchain-anthropic",
-    "langchain-google-genai",
-    "langchain-aws",
-    "langchain-ollama",
+    "langchain-openai>=1.2,<2",
+    "langchain-anthropic>=1.4,<2",
+    "langchain-google-genai>=4.2,<5",
+    "langchain-aws>=1.4,<2",
+    "langchain-ollama>=1.1,<2",
 ]
 dev = [
```

**Rationale per pin**:

| Pin change | Why |
|---|---|
| `langchain` add `<2` | Forward protection. Upstream did the 0.x→1.x major break; the next one is `<2`'s job to catch. |
| `langchain-core` add `<2` | Same. Coherent-major constraint matching ADR-ARCH-010-rev2. |
| `langchain-openai>=1.2,<2` | Floor matches resolved version today (1.2.1) and Jarvis-verified set; `<2` cap is forward protection. |
| `langchain-anthropic>=1.4,<2` | Floor = 1.4 (today resolves 1.4.2; Jarvis 1.4.1 — both inside `>=1.4`). `<2` cap. |
| `langchain-google-genai>=4.2,<5` | Floor matches resolved (4.2.2) and Jarvis (4.2.2). Cap is `<5` because this package's major is decoupled from the langchain core 1.x cycle. |
| `langchain-aws>=1.4,<2` | Floor = today's resolved 1.4.5; same `<2` cap. **Not in Jarvis's set** — study-tutor declares this provider where Jarvis does not. |
| `langchain-ollama>=1.1,<2` | Floor = today's resolved 1.1.0; same `<2` cap. **Not in Jarvis's set.** |

**Not changing**:
- `requires-python = ">=3.11"` — already correct per the portfolio guide. Open upper bound is the right call (see §4 of `portfolio-python-pinning.md`).
- `pydantic>=2.0,<3.0` — already correctly pinned with `<3` cap.
- `mcp>=1.0` — Anthropic MCP SDK; not part of the LangChain ecosystem; not subject to the same risk pattern. Leaving as-is.
- `httpx>=0.27`, `click>=8.0`, `pyyaml>=6.0`, `python-dotenv>=1.0` — stable libraries with predictable major-version cadence; capping them buys nothing.

**What this diff does NOT add**:
- `deepagents` — not currently imported (see §3). Defer.
- `langgraph` direct pin — not imported (see §2). Transitive `<2` is implied by `langchain<2`. Defer indefinitely.
- `langchain-tavily` or other Jarvis providers not in study-tutor's `[providers]` — keep the surface lean.

---

## 5. Draft ADR

Filename: `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`

(Numbering: ADR-ARCH-019 is the latest; ADR-ARCH-020 is the next free slot.)

````markdown
# ADR-ARCH-020 — LangChain ecosystem 1.x pinning + Python 3.14 alignment

## Status

Accepted

**Date:** 2026-04-29
**Phase:** Phase 0 (forward protection; no runtime behaviour change)
**Related:** ADR-ARCH-004 (stack), ADR-ARCH-012 (deepagents AsyncSubAgent),
[Jarvis ADR-ARCH-010 rev2] (`appmilla_github/jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`),
[GuardKit portfolio guide] (`appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md`),
[FA04 review] (`appmilla_github/guardkit/.claude/reviews/TASK-REV-FA04-report.md`)

## Context

The GuardKit AutoBuild trapdoor incident (FA04, 2026-04-27) traced a 33-minute
Jarvis stall to the combination of:

1. A stale `requires-python = ">=3.12,<3.13"` cap excluding the active
   `/usr/local/bin/python3` (3.14 since 2025-10-07).
2. Open-floor LangChain ecosystem pins (`langchain-core>=0.3`, `langgraph>=0.3`,
   `langchain-anthropic>=0.2`, etc.) that let the resolver pick mismatched
   0.x / 1.x pairs and produce runtime
   `ModuleNotFoundError: No module named 'langchain_core.messages.block_translators.langchain_v0'`.

Jarvis's remediation (ADR-ARCH-010 rev2): `requires-python = ">=3.11"` + coherent
`<2` caps on the LangChain ecosystem.

study-tutor's posture pre-review:

- `requires-python = ">=3.11"` ✓ (already correct).
- `langchain>=1.2.11` and `langchain-core>=1.2.18` ✓ (1.x runtime floor).
- Five providers in `[project.optional-dependencies].providers` declared with
  **no version constraint** (`langchain-openai`, `langchain-anthropic`,
  `langchain-google-genai`, `langchain-aws`, `langchain-ollama`).

Empirical run on Python 3.14.2 (2026-04-29, this ADR's evidence file):
`uv pip install -e ".[dev,providers]"` resolved cleanly and `pytest` reported
**23/23 passing in 6.84s** with zero `langchain`-runtime failures. The unpinned
providers happen to resolve today to the same coherent 1.x set Jarvis verified
on 3.14 — but "happens to" is exactly the structural problem rev2 solved.

## Decision

Pin the LangChain ecosystem to coherent 1.x with explicit caps, matching Jarvis
ADR-ARCH-010 rev2 where applicable:

| Package | Pin | Notes |
|---|---|---|
| `langchain` | `>=1.2.11,<2` | Add `<2` cap (floor unchanged). |
| `langchain-core` | `>=1.2.18,<2` | Add `<2` cap (floor unchanged). |
| `langchain-openai` | `>=1.2,<2` | Floor matches today's resolved 1.2.1. |
| `langchain-anthropic` | `>=1.4,<2` | Floor matches today's resolved 1.4.2. |
| `langchain-google-genai` | `>=4.2,<5` | Floor matches today's resolved 4.2.2. |
| `langchain-aws` | `>=1.4,<2` | Floor matches today's resolved 1.4.5. *(study-tutor only — not in Jarvis's pin set.)* |
| `langchain-ollama` | `>=1.1,<2` | Floor matches today's resolved 1.1.0. *(study-tutor only — not in Jarvis's pin set.)* |

`requires-python = ">=3.11"` is **unchanged** — already correct per the portfolio
guide. No upper bound on Python.

## What this ADR deliberately does NOT change

- **`deepagents` not added.** ADR-ARCH-004 and ADR-ARCH-012 declare
  `deepagents>=0.5.3` for Phase 1 (`AsyncSubAgent` Coach + `CompositeBackend`
  routing), but Phase 0 code does not import it and Phase 0's `pyproject.toml`
  does not declare it. Adding the pin without a corresponding import to
  validate against would just defer the same audit. When Phase 1 implementation
  begins importing `AsyncSubAgent`, it should add
  `deepagents>=0.5.3,<0.6` (matching Jarvis's pin) and revalidate this ADR.
- **`langgraph` not added as a direct dep.** Source code grep confirms zero
  imports; `langgraph` enters the dependency graph transitively via
  `langchain → langgraph`. The `langchain<2` cap implies `langgraph<2` for
  this codebase. Declaring it directly would create a maintenance obligation
  (every future bump needs revalidation) for zero protection benefit.
  *Diverges from Jarvis intentionally.*
- **`requires-python` upper bound not added.** Per
  `guardkit/docs/guides/portfolio-python-pinning.md`: closed Python upper
  bounds decay silently into trapdoors (the FA04 mechanism). Defensive
  protection for unknown future Python minors belongs in CI matrices and
  known-bad version exclusions, not in `requires-python`.

## Verified versions (Python 3.14.2 venv, 2026-04-29)

Empirical evidence for the chosen floors:

| Package | Resolved on 3.14 | Floor in this ADR | Status |
|---|---|---|---|
| `langchain` | 1.2.15 | `>=1.2.11` | ✓ |
| `langchain-core` | 1.3.2 | `>=1.2.18` | ✓ |
| `langchain-openai` | 1.2.1 | `>=1.2` | ✓ |
| `langchain-anthropic` | 1.4.2 | `>=1.4` | ✓ |
| `langchain-google-genai` | 4.2.2 | `>=4.2` | ✓ |
| `langchain-aws` | 1.4.5 | `>=1.4` | ✓ |
| `langchain-ollama` | 1.1.0 | `>=1.1` | ✓ |
| `langgraph` (transitive) | 1.1.10 | implied `<2` via `langchain<2` | ✓ |
| `mcp` | 1.27.0 | `>=1.0` (unchanged) | ✓ |
| `pydantic` | 2.13.3 | `>=2.0,<3.0` (unchanged) | ✓ |

**Test outcome**: 23/23 passing, 6.84s, zero langchain-runtime failures.

This evidence is captured in `.claude/reviews/TASK-REV-57BD-report.md` (this
ADR's review record).

## Alternatives considered

1. **Do nothing** *(rejected)*. The unpinned providers are a forward-protection
   gap. The FA04 mechanism specifically requires *future* breaking changes plus
   stale pins; today's clean resolution offers no protection against the next
   coordinated 1.x→2.x bump.
2. **Match Jarvis's pin set verbatim** *(rejected)*. Would require adding
   `deepagents` and `langgraph` direct deps that this codebase doesn't import.
   The portfolio guide is explicit that the recipe is calibrated per consumer,
   not copy-pasted across.
3. **Use exact version pins** *(rejected)*. Too strict — patch releases that
   fix bugs would be blocked. Floor + same-major cap is the right granularity
   for an applications-not-libraries posture.
4. **Closed upper bound on Python** *(rejected)*. Direct cause of FA04. See
   the portfolio guide for the full case.

## Consequences

**Positive:**
- Forward protection against the FA04 mechanism (mismatched majors after a
  coordinated ecosystem bump). Same protection Jarvis has post-rev2.
- Empirically validated on the same Python (3.14) the autobuild orchestrator
  uses on the demo machine.
- Deliberately leaner pin surface than Jarvis — reflects study-tutor's actual
  imports, not a copy-pasted superset.

**Negative:**
- Adds a calendar-cadence revalidation obligation when LangChain ships 2.x
  (the cap will need lifting). The new ADR at that point can re-verify the
  upgrade against this evidence baseline.
- Adds two providers (`langchain-aws`, `langchain-ollama`) to the pin-tracking
  surface that don't exist in Jarvis. Cross-portfolio reviews will need to
  notice the divergence — recorded here so that's auditable.

**Neutral:**
- `deepagents` Phase 1 question (§3 of the review) is not answered by this ADR
  and is captured as a separate follow-up.

## References

- Jarvis ADR-ARCH-010 rev2 (cross-repo precedent, recipe source).
- TASK-REV-FA04 review (origin incident).
- `guardkit/docs/guides/portfolio-python-pinning.md` (Python pinning rationale).
- `.claude/reviews/TASK-REV-57BD-report.md` (this ADR's evidence record).
````

---

## 6. ADR/codebase discrepancy: deepagents not in pyproject.toml

**Finding (orthogonal to the pin alignment, surfaced during this review):**

ADR-ARCH-004 §Decision and ADR-ARCH-012 §Decision both declare
`deepagents>=0.5.3` in `[providers]`. Current `pyproject.toml` does not declare
`deepagents` anywhere; current `src/` and `tests/` do not import it.

This is **pre-existing** — not caused by, and not resolved by, this review's
pin work. It needs its own follow-up:

- If Phase 1 is the right time to add the dep, the new pin can be
  `deepagents>=0.5.3,<0.6` (matching Jarvis ADR-ARCH-010 §Decision).
- If Phase 1 architecture has shifted away from `AsyncSubAgent`, ADR-ARCH-012
  needs revising (or superseding) and the dependency declaration is moot.

Flagging this as a follow-up is the right move — the review's scope is
"alignment with FA04/rev2 recipe", and the recipe deliberately doesn't add
deepagents to consumers that don't import it.

---

## 7. Should study-tutor reference the portfolio-pinning guide in `CLAUDE.md`?

**Recommendation: Yes, but lightly.**

study-tutor's existing `CLAUDE.md` (and AGENTS.md) doesn't cross-reference
GuardKit's portfolio guide. Adding a one-paragraph "When changing
`requires-python` or LangChain ecosystem pins, see
`guardkit/docs/guides/portfolio-python-pinning.md`" pointer would:

- Make the constraint discoverable in-repo (the next maintainer doesn't have
  to know to look in GuardKit for it).
- Match what should arguably also be done in Jarvis, forge, etc. as part of
  portfolio-wide stewardship — but those are separate repos' decisions.

Suggested addition (somewhere near the existing dependency / Phase 0 section
of `CLAUDE.md`):

```markdown
### Pinning policy

Python: `>=3.11`, **no upper bound** (per
`guardkit/docs/guides/portfolio-python-pinning.md`). Closed upper bounds in
`requires-python` decay into trapdoors (see TASK-REV-FA04).

LangChain ecosystem: coherent 1.x with `<2` caps and explicit floors (see
ADR-ARCH-020). When the floors need lifting (a real bug fix in a newer
patch / minor), update `pyproject.toml` and the verified-versions table in
ADR-ARCH-020 in the same commit.
```

This is **out of scope for the [I]mplement option**'s subtask list unless
explicitly added — flagging as a "while you're in there" change.

---

## 8. Acceptance criteria — status

- [x] Empirical 3.14 + `uv pip install --upgrade -e ".[dev,providers]"` succeeds and `.venv/bin/python -c "import study_tutor"` works. *(§1.1)*
- [x] Full pytest run captured. *(§1.2; 23/23 in `/tmp/study-tutor-3.14-pytest.log`)*
- [x] Resolved versions table for all `langchain-*` packages documented. *(§1.3)*
- [x] Failure categorisation — N/A (zero failures). *(§1.2)*
- [x] Provider-pin recommendation: explicit diff against current `pyproject.toml`. *(§4)*
- [x] Confirmation that `langgraph` is not used in the codebase. *(§2 — grep evidence; transitive only via `langchain`)*
- [x] New ADR drafted. *(§5 — ADR-ARCH-020)*
- [x] Recommendation on `CLAUDE.md` portfolio guide reference. *(§7 — yes, lightly)*
- [x] No proposed changes to GuardKit or Jarvis. *(All recommendations are study-tutor-side)*
- [x] Report saved to `.claude/reviews/TASK-REV-57BD-report.md`. *(this file)*

---

## 9. Findings summary

| # | Finding | Severity | Evidence |
|---|---|---|---|
| F1 | study-tutor's runtime LangChain pins (`langchain`, `langchain-core`) lack `<2` caps. | Low (forward protection) | `pyproject.toml:15-16` |
| F2 | All five `[providers]` packages are completely unpinned. | Medium (forward protection — exactly the FA04 pattern) | `pyproject.toml:27-32` |
| F3 | `langgraph` is a transitive dep, not imported. | Informational | grep `--include="*.py"`: 0 hits |
| F4 | `deepagents` declared in ADR-ARCH-004/012 but absent from `pyproject.toml` and source. | Medium (pre-existing ADR/code drift; separate from pin alignment) | grep + `pyproject.toml` |
| F5 | `requires-python = ">=3.11"` already correct. | Positive | `pyproject.toml:9` |
| F6 | `pydantic>=2.0,<3.0` already correctly capped. | Positive | `pyproject.toml:12` |
| F7 | Empirical 3.14 install + 23/23 tests passing. | Positive (cleaner baseline than Jarvis on rev2) | §1 |

---

## 10. Recommendations

| # | Recommendation | Effort | Impact | Mode |
|---|---|---|---|---|
| R1 | Add `<2` caps to `langchain`, `langchain-core` runtime deps. | XS (2 lines) | Forward protection vs FA04-class breakage | direct |
| R2 | Add explicit floors + `<2` caps to all five `[providers]` packages. | XS (5 lines) | Forward protection; locks in Jarvis-verified versions | direct |
| R3 | File ADR-ARCH-020 capturing the pin recipe + verified-versions table + langgraph/deepagents non-decisions. | S (one new file) | Auditable trail; cross-repo precedent reference | direct |
| R4 | Add a "Pinning policy" pointer to `CLAUDE.md` referencing the GuardKit portfolio guide and ADR-ARCH-020. | XS (one paragraph) | Discoverability for the next maintainer | direct |
| R5 | (Follow-up, separate task) Resolve the ADR-ARCH-004/012 vs `pyproject.toml` deepagents discrepancy when Phase 1 implementation begins. | M (Phase 1 architecture decision) | Aligns ADRs with reality; gates `AsyncSubAgent` Coach work | task-work |

R1+R2+R3+R4 are all small, mechanical, parallel-safe changes scoped to
`pyproject.toml`, one new ADR, and a few lines in `CLAUDE.md`. They're a
natural single-PR bundle. R5 is genuinely a separate Phase 1 decision and
should not be folded into the pin-alignment commit.

---

## Decision Options

**[A]ccept** — Approve findings; archive review. Pin diff (§4) and ADR
(§5) become reference artefacts; no code changes are made by accepting.

**[I]mplement** — Create implementation subtasks for R1, R2, R3, R4 (and
optionally R5). Recommended subtask split:

1. Update `pyproject.toml` (R1 + R2 in one commit — they're trivially
   coupled).
2. Add `docs/architecture/decisions/ADR-ARCH-020-...md` (R3).
3. Add Pinning policy paragraph to `CLAUDE.md` (R4).
4. (Optional, separate feature) Resolve deepagents ADR/code drift (R5).

**[R]evise** — Request additional analysis. Possible additions:
- Explicit cross-check of every transitive 1.x package's compatibility with
  the new caps (deeper than today's pip-list-based comparison).
- Pre-flight against Jarvis's `test_phase2_dependencies.py`-style pin-tracking
  guard tests — should study-tutor add equivalent guard tests?

**[C]ancel** — Discard review.
