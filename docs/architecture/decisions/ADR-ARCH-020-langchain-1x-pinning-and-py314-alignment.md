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
