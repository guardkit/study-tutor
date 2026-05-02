I think we need to close out the issues originally marked as must complete for Phase 1 close-out. please update tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md as we are NOT to use any cloud AI API's due to cost, all LLM's are served locally onthe GB10 via the TailScale network using lama-swap see /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark. Please investigate the usage of Graphiti in the guardkit repo - this has all been solved in there I'm sure and maybe we can create some tasks to pull out the Graphiti clients etc into a core library for use across repos - the study-tutor, guardkit and specialist-agent will alll use Graphiti heavily and then update the task accordingly

Here's the Phase 1 close-out gate report. We're on Saturday 2 May, so any reds slip Saturday's start by their fix-time per the build plan's own slip rule.

Phase 1 Close-Out — Gate Status
✅ Gate 1 — FEAT-PH1-004 / FEAT-70A4: PATH A (shipped)
Finalized merge at commit 6eb41a7 (1 May): chore(FEAT-70A4): finalize merge — archive, move tasks, clean autobuild state.
All seven PRV tasks in tasks/completed/ (TASK-PRV-001..007).
Verifier integrated into src/study_tutor/tutoring/orchestrator.py:32-461 (QuoteVerifierLike Protocol, _apply_coach_handover, verify call inside the turn pipeline).
Six-criterion rubric live: src/study_tutor/tutoring/coach/rubric.py:200 shows quote_fidelity=0.20 weight in defaults; weighted-sum and to_dict both include it.
One residual cleanup: tasks/in_review/TASK-REV-AB7A-analyze-failed-autobuild-feat-70a4.md is status: review_complete but still in in_review/. Move-to-completed sweep, not a blocker.
🟡 Gate 2 — Lilymay seeded: CODE READY, RUN UNVERIFIED
scripts/seed_student_model.py is fully implemented, idempotent, defaults to Synology whitestocks:6379, has the --student lilymay arg, and exits cleanly if a prior seed is detected. No regressions.
I cannot verify from repo state whether python scripts/seed_student_model.py --student lilymay was actually run against your Synology FalkorDB and that get_student_state("lilymay") returns the expected baseline. Need your confirmation — or 5 minutes to run it.
🟡 Gate 3 — End-to-end MCP demo session: NO EVIDENCE FOUND
No session-export artifact, log, or note in docs/state/, docs/research/ideas/, or anywhere else suggests tutor_start_session → 5-7× tutor_turn → tutor_session_end has been driven from Claude Desktop with a Coach revision and a session_completed episode written.
Phase 1 build plan line 5 explicitly flagged this as not-yet-done as of write-time (30 April). Need your confirmation — likely needs to be done today.
✅ Gate 4 — Parity surfaces SR-01..SR-09: GREEN (one env caveat)
tests/unit + tests/smoke: 692/693 pass with the .venv on PATH. Integration: 3/3 pass.
The single failure — tests/unit/planner/test_protocols.py:117 test_mypy_strict_accepts_structurally_conforming_rule — is not a regression. It was last touched in commit 1e37d7e (FEAT-PH1-002). Root cause: mypy is installed at /Library/Frameworks/Python.framework/Versions/3.14/bin/mypy (system Python), not in .venv, so the subprocess call cannot resolve the editable study_tutor install. Fix is a one-liner: .venv/bin/pip install mypy. Code health is fine.
The 3 stdio/subprocess tests (SR-04 stdio discipline, Graphiti subprocess) pass once the venv bin is on PATH for the pytest invocation.
❌ Gate 5 — phase-1-validation.md seeded: RED (file missing)
docs/research/ideas/ has every other phase doc (phase-0-validation.md, phase-1-build-plan.md, phase-1-scope.md, phase-2-build-plan.md, phase-2-scope.md) but no phase-1-validation.md.
Per the build plan's own §Day 1 step 1, Saturday morning's first task is to finalise this file — which assumes the four-paragraph outline (held / drifted / falsified / changes-current-phase) was seeded Friday evening. It wasn't.
Recommendation
The cheapest path to clear Saturday's start is to seed phase-1-validation.md now (5–10 min) and run the two Phase-1 G2/G3 runtime checks (Lilymay seed + 5–7-turn MCP session) before crossing the boundary into FEAT-PH2-001.

Concretely, if you're ready, I can:

Create docs/research/ideas/phase-1-validation.md with the four-paragraph outline, prefilled with what's already known (FEAT-70A4 shipped → Path A; six-criterion Coach live; SR-01..SR-09 green; Reachy delivery confirmed).
Walk through the Lilymay seed run and the end-to-end MCP demo session with you (driven from Claude Desktop), capturing the session-export and turn latency for the phase-1-validation.md "drifted" / "held" buckets.
Want me to start with (1) — seed the validation doc — so you can fill in the runtime numbers as you do the seed + demo session?

please run Gate 2 — Lilymay seeded: CODE READY, RUN UNVERIFIED
Bash Find script CLI surface
IN
grep -n "argparse\|add_argument\|--student\|--dry-run\|def main\|asyncio.run" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py | head -25

OUT
60:import argparse
302:def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
304:    parser = argparse.ArgumentParser(
311:    parser.add_argument(
615:async def main(argv: list[str] | None = None) -> int:
618:    Wired to ``asyncio.run`` from the ``__main__`` block so callers and
627:    # ``asyncio.run`` exits with the right status without us hand-rolling
651:        sys.exit(asyncio.run(main()))
Bash Check env vars (redacted)
IN
grep -E "^GRAPHITI_|^GRAPH_DB_|^FALKOR|^OPENAI_API_KEY|^GOOGLE_API_KEY|^GEMINI" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.env | sed 's/=.*/=<set>/'

OUT
OPENAI_API_KEY=<set>
GOOGLE_API_KEY=<set>
Read seed_student_model.py (lines 281-370)
The script seeds Lilymay by default (no --student arg needed — single-learner design). It's idempotent against the Synology defaults (whitestocks:6379, db study_tutor). Running it now.

Bash Verify dotenv + API keys reachable
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "import dotenv; dotenv.load_dotenv('.env'); import os; print('GOOGLE_API_KEY set:', bool(os.environ.get('GOOGLE_API_KEY')))" 2>&1

OUT
GOOGLE_API_KEY set: True
Bash Quick FalkorDB reachability ping
IN
redis-cli -h whitestocks -p 6379 ping 2>&1 | head -5

OUT
PONG
FalkorDB reachable, env keys load. Running the seed.

Bash Run Lilymay seed against Synology FalkorDB
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m dotenv -f .env run -- /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python scripts/seed_student_model.py 2>&1 | tail -80

OUT
2026-05-02 07:21:33,089 WARNING study_tutor.knowledge.graphiti_client: graphiti client degraded: ImportError
2026-05-02 07:21:33,089 ERROR study_tutor.seed: seeding failed: graphiti client unavailable
Bash Check graphiti_core install
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "import graphiti_core; print(graphiti_core.__version__)" 2>&1; echo "---"; /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/pip list 2>/dev/null | grep -i "graphiti\|falkor"

OUT
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import graphiti_core; print(graphiti_core.__version__)
    ^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'graphiti_core'
---
Bash Check pyproject for graphiti dep
IN
grep -n "graphiti\|falkor" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/pyproject.toml | head -20

OUT
(Bash completed with no output)
Bash Read pyproject.toml head
IN
cat /Users/richardwoollcott/Projects/appmilla_github/study-tutor/pyproject.toml | head -80

OUT
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "study-tutor"
version = "0.1.0"
description = "Fine-tuned English tutoring runtime (MCP adapter + LLM client) for GCSE literature tutoring"
requires-python = ">=3.11"
license = {text = "MIT"}
dependencies = [
    "pydantic>=2.0,<3.0",
    "pyyaml>=6.0",
    "click>=8.0",
    "langchain>=1.2.11,<2",
    "langchain-core>=1.2.18,<2",
    "python-dotenv>=1.0",
    "mcp>=1.0",
    "httpx>=0.27",
]

[project.scripts]
study-tutor = "study_tutor.cli.main:cli"

[project.optional-dependencies]
providers = [
    "langchain-openai>=1.2,<2",
    "langchain-anthropic>=1.4,<2",
    "langchain-google-genai>=4.2,<5",
    "langchain-aws>=1.4,<2",
    "langchain-ollama>=1.1,<2",
]
dev = [
    "pytest>=9.0.2",
    "pytest-asyncio>=0.23",
    "pytest-cov",
    # TASK-OPS-BDDM-11 / FEAT-BDDM (2026-04-26): proactive add. study-tutor
    # currently has zero `.feature` files, so there is no active silent-bypass
    # risk today, but pytest-bdd must be importable in any worktree where
    # GuardKit's bdd_runner might execute, so the absence of feature files
    # cannot mask a missing dependency the moment the first .feature lands.
    # See guardkit:tasks/.../TASK-OPS-BDDM-11-pyproject-study-tutor.md.
    "pytest-bdd>=8.1,<9",
]

[tool.hatch.build.targets.wheel]
packages = ["src/study_tutor"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
# ``pythonpath = ["."]`` makes the repo root importable so that
# ``scripts/seed_student_model.py`` (TASK-GSM-006) can be reached as
# ``scripts.seed_student_model`` by the seam + unit tests. Hatchling only
# installs ``src/study_tutor`` into site-packages, so without this entry
# the seeding script — which intentionally lives outside the package —
# would be unimportable from tests.
#
# ``"src"`` is also included so the worktree's ``src/study_tutor`` (rather
# than the parent repo's editable install) is the one tests resolve. Git
# worktrees share the parent repo's ``.venv``, and that .venv has the
# parent repo's ``src/`` baked into ``sys.path`` ahead of any worktree
# code; without this entry the worktree's in-flight changes to
# ``study_tutor`` wouldn't be visible to its own tests.
pythonpath = ["src", "."]
markers = [
    "seam: integration-contract seam tests between GuardKit tasks",
    "integration_contract: marks the specific contract under test (arg: contract name)",
    "smoke: fast end-to-end-ish smoke tests run by autobuild smoke gates",
    "feat_ph1_002: tests scoped to the Deterministic Session Planner feature (FEAT-PH1-002)",
    "feat_ph1_003: tests scoped to the DeepAgents Tutoring Loop with Coach feature (FEAT-PH1-003)",
]
Bash Find graphiti_core import pattern
IN
grep -rn "graphiti_core\|graphiti-core" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py /Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/graphiti_latency_spike.py 2>/dev/null | head -15

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:3:FEAT-1773 / TASK-GSM-003 — owns the lifecycle of a ``graphiti-core`` client
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:8:   feature spec) — the module loads successfully even when ``graphiti-core``
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:9:   is not installed. ``import graphiti_core`` happens *inside* the
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:10:   ``_load_graphiti_core`` helper, never at module top level. A top-level
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:11:   ``try: import graphiti_core`` would still execute at import time and
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:68:        llm_provider: Backing LLM provider for graphiti-core (default
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:115:def _load_graphiti_core() -> tuple[Any, Any]:
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:116:    """Lazy-import ``graphiti-core`` symbols at call time.
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:125:        ImportError: When ``graphiti-core`` is not installed in the active
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:128:    from graphiti_core import Graphiti  # type: ignore[import-not-found]
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:129:    from graphiti_core.driver.falkordb_driver import (  # type: ignore[import-not-found]
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:137:    """Thin lifecycle wrapper around a ``graphiti-core`` client.
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:156:        """The underlying ``graphiti-core`` client, or ``None`` after close."""
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:199:        graphiti-core exposes its underlying driver on the ``driver``
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:203:        graphiti-core minor-version bump that renames the method doesn't
Bash Find graphiti install instructions
IN
grep -rn "pip install\|graphiti_core\|graphiti-core" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/RUNBOOK-open-webui-tutor-access.md /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-1-build-plan.md 2>/dev/null | head -10

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-1-build-plan.md:52:- [ ] `graphiti-core` installed in study-tutor venv: `.venv/bin/pip install graphiti-core`
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-1-build-plan.md:199:6. **Implement the Graphiti client wrapper.** Create `src/study_tutor/knowledge/graphiti_client.py`. Follow the specialist-agent pattern: lazy import of graphiti-core, fail gracefully if unavailable (logged warning, return None from queries), typed exception surface. Copy the lazy-import shape from `specialist-agent/src/specialist_agent/tools/graphiti_client.py`. *(→ TASK-GSM-003)*
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-1-build-plan.md:506:| `pyproject.toml` | Ensure `graphiti-core` is declared (may move out of `[providers]` into a separate `[knowledge-graph]` extra) |
The seed failed because graphiti-core isn't in the venv. It's a soft dependency (excluded from pyproject.toml by design — the code degrades gracefully — but phase-1-build-plan.md:52 lists .venv/bin/pip install graphiti-core as a Phase-1 setup prerequisite that was never run).

Installing into the project venv now (reversible — pip uninstall graphiti-core rolls it back).

Bash Install graphiti-core into venv
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/pip install graphiti-core 2>&1 | tail -15

OUT
(eval):1: no such file or directory: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/pip
Bash List venv bin
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/ | head -20

OUT
activate
activate_this.py
activate.bat
activate.csh
activate.fish
activate.nu
activate.ps1
coverage
coverage-3.14
coverage3
deactivate.bat
distro
dotenv
f2py
filetype
gherkin
httpx
jp.py
jsondiff
jsonpatch
Bash Find pip/python in venv
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/ | grep -E "^pip|^python"

OUT
python
python3
python3.14
Bash Check uv / pip-as-module
IN
which uv 2>/dev/null; /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m pip --version 2>&1 | head -3

OUT
/opt/homebrew/bin/uv
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python: No module named pip
Bash Install graphiti-core via uv
IN
uv pip install graphiti-core 2>&1 | tail -20

OUT
Resolved 27 packages in 428ms
Prepared 1 package in 98ms
Installed 5 packages in 21ms
 + backoff==2.2.1
 + graphiti-core==0.29.0
 + neo4j==6.1.0
 + posthog==7.14.0
 + pytz==2026.1.post1
Bash Verify graphiti_core + FalkorDriver importable
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "import graphiti_core; print(graphiti_core.__version__)" 2>&1; echo "---falkordb driver check---"; /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "from graphiti_core.driver.falkordb_driver import FalkorDriver; print('ok')" 2>&1

OUT
Exit code 1
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import graphiti_core; print(graphiti_core.__version__)
                                ^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: module 'graphiti_core' has no attribute '__version__'
---falkordb driver check---
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    from graphiti_core.driver.falkordb_driver import FalkorDriver; print('ok')
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 31, in <module>
    raise ImportError(
    ...<2 lines>...
    ) from None
ImportError: falkordb is required for FalkorDriver. Install it with: pip install graphiti-core[falkordb]
Bash Install graphiti-core with falkordb extra
IN
uv pip install "graphiti-core[falkordb]" 2>&1 | tail -10

OUT
Resolved 31 packages in 347ms
Prepared 2 packages in 162ms
Installed 2 packages in 2ms
 + falkordb==1.6.1
 + redis==7.4.0
Bash Re-verify FalkorDriver importable
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "from graphiti_core.driver.falkordb_driver import FalkorDriver; print('ok')" 2>&1

OUT
ok
Now re-running the seed.

Bash Seed Lilymay (re-run)
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m dotenv -f .env run -- /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python scripts/seed_student_model.py 2>&1 | tail -60

OUT
2026-05-02 07:22:39,034 INFO study_tutor.knowledge.graphiti_client: graphiti client ready in 533ms
2026-05-02 07:22:39,038 ERROR study_tutor.seed: seeding failed with unhandled exception
Traceback (most recent call last):
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py", line 651, in <module>
    sys.exit(asyncio.run(main()))
             ~~~~~~~~~~~^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/runners.py", line 204, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/runners.py", line 127, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 719, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py", line 634, in main
    return await seed_lilymay(client, helper)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py", line 549, in seed_lilymay
    state = await get_student_state(client, STUDENT_ID)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py", line 332, in get_student_state
    inner.search_nodes(group_ids, ""),
    ^^^^^^^^^^^^^^^^^^
AttributeError: 'Graphiti' object has no attribute 'search_nodes'
Bash Find Graphiti search methods
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "from graphiti_core import Graphiti; print([m for m in dir(Graphiti) if 'search' in m.lower() or 'node' in m.lower()])"

OUT
['_extract_and_dedupe_nodes_bulk', '_extract_and_resolve_nodes', '_resolve_nodes_and_edges_bulk', '_search', 'get_nodes_and_edges_by_episode', 'search', 'search_']
Bash Check queries.py search calls
IN
grep -n "search_nodes\|search_facts\|search(" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py | head -15

OUT
4:holds the only call sites in Phase 1 that touch ``search_nodes`` /
332:                inner.search_nodes(group_ids, ""),
Read queries.py (lines 301-360)
why not just use the MCP?
Fair point — graphiti's search MCP can verify existing state directly without going through the broken seed-script path.

Bash Find Lilymay group_id prefix
IN
grep -n "STUDENT_GROUP_PREFIX\|group_id\|group:" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py 2>/dev/null | head -10

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:6:``group_ids`` from the constants in :mod:`study_tutor.knowledge.student_model`
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:37:    STUDENT_GROUP_PREFIX,
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:111:    year_group: int | None = None
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:327:    group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:332:                inner.search_nodes(group_ids, ""),
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:333:                inner.search_memory_facts(group_ids, ""),
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:490:    group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:494:        group_ids=group_ids,
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:58:STUDENT_GROUP_PREFIX: str = "student:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:167:    year_group: int = Field(
Group prefix is student:, so the Lilymay group_id is student:lilymay. Querying Graphiti directly.

Graphiti [get_status]
OUT
{"status":"ok","message":"Graphiti MCP server is running and connected to falkordb database"}
Graphiti [search_nodes]Lilymay
OUT
{"result":{"error":"Error searching nodes: RediSearch: Syntax error at offset 19 near student"}}
Graphiti [search_nodes]Lilymay
OUT
{"result":{"message":"No relevant nodes found","nodes":[]}}
Graphiti [get_episodes]
OUT
{"result":{"message":"No episodes found","episodes":[]}}
Graphiti is reachable but Lilymay is not seeded — empty result for both nodes and episodes. So Gate 2 is genuinely red, but there's a deeper blocker.

Bash Find graphiti version pin and test mock shape
IN
grep -rn "search_nodes\|search_memory_facts" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py 2>/dev/null | head -10; echo "---versions---"; grep -rn "graphiti-core\|graphiti_core" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit 2>/dev/null | grep -E "0\.|>=|==|version" | head -10

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:8:  ``event=student_state_read_timeout`` (mocked slow ``search_nodes``).
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:75:        self.search_nodes_calls: list[dict[str, Any]] = []
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:76:        self.search_memory_facts_calls: list[dict[str, Any]] = []
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:78:    async def search_nodes(self, group_ids: list[str], query: str) -> list[Any]:
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:79:        self.search_nodes_calls.append({"group_ids": group_ids, "query": query})
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:84:    async def search_memory_facts(
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:87:        self.search_memory_facts_calls.append(
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:193:    assert inner.search_nodes_calls[0]["group_ids"] == expected_group_ids
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:194:    assert inner.search_memory_facts_calls[0]["group_ids"] == expected_group_ids
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py:464:    search_methods = {"search_nodes", "search_memory_facts"}
---versions---
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/player_turn_2.json:75:      "evidence": "get_client() implements the three documented degradation gates: (1) ImportError from _load_graphiti_core \u2192 log + return None; (2) any exception from FalkorDriver(...) or Graphiti(...) construction \u2192 log + return None; (3) healthcheck() returning False (timeout or driver exception) \u2192 log + close partial wrapper + return None. No exception escapes. Verified by test_get_client_returns_none_when_graphiti_core_import_fails (patches _load_graphiti_core to raise ImportError), test_get_client_returns_none_when_driver_construction_fails (driver_cls side_effect=ConnectionRefusedError), and test_get_client_returns_none_when_healthcheck_times_out (slow driver + 0.05s timeout). All three assert result is None and pass.",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/player_turn_2.json:105:      "evidence": "All degradation paths funnel through _log_degraded(error_class, host, *, latency_ms=None, error_message=None) which calls logger.warning with extra={event: 'graphiti_client_degraded', error_class, falkor_host, degraded: True, latency_ms?, error_message?}. EVENT_DEGRADED is a module constant. Tests assert these LogRecord attributes via getattr(rec, 'event', None) == mod.EVENT_DEGRADED, rec.error_class, rec.falkor_host, rec.degraded is True. Covered by test_get_client_returns_none_when_graphiti_core_import_fails, test_get_client_returns_none_when_driver_construction_fails, test_get_client_returns_none_when_healthcheck_times_out, and test_healthcheck_returns_false_when_driver_raises.",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/coach_turn_2.json:40:      "evidence": "get_client() implements the three documented degradation gates: (1) ImportError from _load_graphiti_core \u2192 log + return None; (2) any exception from FalkorDriver(...) or Graphiti(...) construction \u2192 log + return None; (3) healthcheck() returning False (timeout or driver exception) \u2192 log + close partial wrapper + return None. No exception escapes. Verified by test_get_client_returns_none_when_graphiti_core_import_fails (patches _load_graphiti_core to raise ImportError), test_get_client_returns_none_when_driver_construction_fails (driver_cls side_effect=ConnectionRefusedError), and test_get_client_returns_none_when_healthcheck_times_out (slow driver + 0.05s timeout). All three assert result is None and pass.",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/coach_turn_2.json:41:      "notes": "get_client() implements the three documented degradation gates: (1) ImportError from _load_graphiti_core \u2192 log + return None; (2) any exception from FalkorDriver(...) or Graphiti(...) construction \u2192 log + return None; (3) healthcheck() returning False (timeout or driver exception) \u2192 log + close partial wrapper + return None. No exception escapes. Verified by test_get_client_returns_none_when_graphiti_core_import_fails (patches _load_graphiti_core to raise ImportError), test_get_client_returns_none_when_driver_construction_fails (driver_cls side_effect=ConnectionRefusedError), and test_get_client_returns_none_when_healthcheck_times_out (slow driver + 0.05s timeout). All three assert result is None and pass."
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/coach_turn_2.json:64:      "evidence": "All degradation paths funnel through _log_degraded(error_class, host, *, latency_ms=None, error_message=None) which calls logger.warning with extra={event: 'graphiti_client_degraded', error_class, falkor_host, degraded: True, latency_ms?, error_message?}. EVENT_DEGRADED is a module constant. Tests assert these LogRecord attributes via getattr(rec, 'event', None) == mod.EVENT_DEGRADED, rec.error_class, rec.falkor_host, rec.degraded is True. Covered by test_get_client_returns_none_when_graphiti_core_import_fails, test_get_client_returns_none_when_driver_construction_fails, test_get_client_returns_none_when_healthcheck_times_out, and test_healthcheck_returns_false_when_driver_raises.",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/coach_turn_2.json:65:      "notes": "All degradation paths funnel through _log_degraded(error_class, host, *, latency_ms=None, error_message=None) which calls logger.warning with extra={event: 'graphiti_client_degraded', error_class, falkor_host, degraded: True, latency_ms?, error_message?}. EVENT_DEGRADED is a module constant. Tests assert these LogRecord attributes via getattr(rec, 'event', None) == mod.EVENT_DEGRADED, rec.error_class, rec.falkor_host, rec.degraded is True. Covered by test_get_client_returns_none_when_graphiti_core_import_fails, test_get_client_returns_none_when_driver_construction_fails, test_get_client_returns_none_when_healthcheck_times_out, and test_healthcheck_returns_false_when_driver_raises."
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/coach_turn_2.json:107:        "evidence": "get_client() implements the three documented degradation gates: (1) ImportError from _load_graphiti_core \u2192 log + return None; (2) any exception from FalkorDriver(...) or Graphiti(...) construction \u2192 log + return None; (3) healthcheck() returning False (timeout or driver exception) \u2192 log + close partial wrapper + return None. No exception escapes. Verified by test_get_client_returns_none_when_graphiti_core_import_fails (patches _load_graphiti_core to raise ImportError), test_get_client_returns_none_when_driver_construction_fails (driver_cls side_effect=ConnectionRefusedError), and test_get_client_returns_none_when_healthcheck_times_out (slow driver + 0.05s timeout). All three assert result is None and pass.",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/coach_turn_2.json:108:        "notes": "get_client() implements the three documented degradation gates: (1) ImportError from _load_graphiti_core \u2192 log + return None; (2) any exception from FalkorDriver(...) or Graphiti(...) construction \u2192 log + return None; (3) healthcheck() returning False (timeout or driver exception) \u2192 log + close partial wrapper + return None. No exception escapes. Verified by test_get_client_returns_none_when_graphiti_core_import_fails (patches _load_graphiti_core to raise ImportError), test_get_client_returns_none_when_driver_construction_fails (driver_cls side_effect=ConnectionRefusedError), and test_get_client_returns_none_when_healthcheck_times_out (slow driver + 0.05s timeout). All three assert result is None and pass."
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/coach_turn_2.json:131:        "evidence": "All degradation paths funnel through _log_degraded(error_class, host, *, latency_ms=None, error_message=None) which calls logger.warning with extra={event: 'graphiti_client_degraded', error_class, falkor_host, degraded: True, latency_ms?, error_message?}. EVENT_DEGRADED is a module constant. Tests assert these LogRecord attributes via getattr(rec, 'event', None) == mod.EVENT_DEGRADED, rec.error_class, rec.falkor_host, rec.degraded is True. Covered by test_get_client_returns_none_when_graphiti_core_import_fails, test_get_client_returns_none_when_driver_construction_fails, test_get_client_returns_none_when_healthcheck_times_out, and test_healthcheck_returns_false_when_driver_raises.",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/TASK-GSM-003/coach_turn_2.json:132:        "notes": "All degradation paths funnel through _log_degraded(error_class, host, *, latency_ms=None, error_message=None) which calls logger.warning with extra={event: 'graphiti_client_degraded', error_class, falkor_host, degraded: True, latency_ms?, error_message?}. EVENT_DEGRADED is a module constant. Tests assert these LogRecord attributes via getattr(rec, 'event', None) == mod.EVENT_DEGRADED, rec.error_class, rec.falkor_host, rec.degraded is True. Covered by test_get_client_returns_none_when_graphiti_core_import_fails, test_get_client_returns_none_when_driver_construction_fails, test_get_client_returns_none_when_healthcheck_times_out, and test_healthcheck_returns_false_when_driver_raises."
Using the graphiti MCP confirmed the answer: Lilymay is not in the graph (no nodes, no episodes for student:lilymay). The MCP also surfaced a deeper problem.

What's actually going on
The seed script uses inner.search_nodes(...) / inner.search_memory_facts(...) (src/study_tutor/knowledge/queries.py:332-333) — but those are graphiti MCP server tool names, not methods on the bare graphiti-core library Graphiti class. The library exposes search, _search, search_, get_nodes_and_edges_by_episode only. The unit tests pass because tests/unit/knowledge/test_queries.py:78 duck-types a fake with those method names; nothing exercises the live library.

This is Phase-1 drift that's been hiding behind mocks. It blocks more than just Gate 2:

Gate 2 (seed) — pre-flight idempotency check fails on inner.search_nodes.
Gate 3 (end-to-end MCP demo) — tutor_start_session → get_student_state hits the same broken call. The tutor runtime cannot read live student state.
FEAT-PH2-001 — gamification rules engine reads GamificationState via the same query layer.
To answer your question directly: yes, the MCP is the right way to talk to graphiti. Three viable paths:

A. Seed Lilymay via mcp__graphiti__add_memory (use the MCP for writes too). Reimplements what the script intends as ~10–15 add_memory calls (Student, Subjects, Texts, Topics, AOs, TopicConfidences). Unblocks Gate 2 today, but the runtime read-path stays broken — Gate 3 still red.

B. Fix queries.py to use graphiti-core 0.29's real API (search / _search instead of the MCP-flavoured names), then re-run the original seeder. Unblocks Gates 2 + 3 properly. Half-day-ish task with new tests; cleanest fix; deserves its own task ticket.

C. Defer the seed entirely, record both gates as deferred-into-Phase-2 in phase-1-validation.md, and start Phase 2 with a "seed + read-path repair" task ahead of FEAT-PH2-001. Keeps the schedule but pushes the integration risk forward.

I'd recommend B — it's the smallest fix that unblocks both gates, and discovering this drift now (before FEAT-PH2-001 piles more reads on top) is exactly the value the close-out gates are meant to deliver. Want me to scope it as a task?

(Side note: I left graphiti-core[falkordb]==0.29.0 installed in .venv. It's listed in phase-1-build-plan.md:52 as a Phase-1 prerequisite — not a regression. Reversible with uv pip uninstall graphiti-core falkordb redis neo4j backoff posthog pytz if you want it gone.)

proceed with B and once complete continue with your recommendation : Recommendation
The cheapest path to clear Saturday's start is to seed phase-1-validation.md now (5–10 min) and run the two Phase-1 G2/G3 runtime checks (Lilymay seed + 5–7-turn MCP session) before crossing the boundary into FEAT-PH2-001.

Concretely, if you're ready, I can:

Create docs/research/ideas/phase-1-validation.md with the four-paragraph outline, prefilled with what's already known (FEAT-70A4 shipped → Path A; six-criterion Coach live; SR-01..SR-09 green; Reachy delivery confirmed).
Walk through the Lilymay seed run and the end-to-end MCP demo session with you (driven from Claude Desktop), capturing the session-export and turn latency for the phase-1-validation.md "drifted" / "held" buckets.
Want me to start with (1) — seed the validation doc — so you can fill in the runtime numbers as you do the seed + demo session?
Starting Path B. Let me understand graphiti-core 0.29's actual search API.

Bash Inspect Graphiti.search APIs
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core import Graphiti
import inspect
sig = inspect.signature(Graphiti.search)
print('search signature:')
print(' ', sig)
print()
sig = inspect.signature(Graphiti.search_)
print('search_ signature:')
print(' ', sig)
print()
print('search docstring:')
print(Graphiti.search.__doc__[:1500] if Graphiti.search.__doc__ else '(none)')
"

OUT
search signature:
  (self, query: str, center_node_uuid: str | None = None, group_ids: list[str] | None = None, num_results=10, search_filter: graphiti_core.search.search_filters.SearchFilters | None = None, driver: graphiti_core.driver.driver.GraphDriver | None = None) -> list[graphiti_core.edges.EntityEdge]

search_ signature:
  (self, query: str, config: graphiti_core.search.search_config.SearchConfig = SearchConfig(edge_config=EdgeSearchConfig(search_methods=[<EdgeSearchMethod.bm25: 'bm25'>, <EdgeSearchMethod.cosine_similarity: 'cosine_similarity'>, <EdgeSearchMethod.bfs: 'breadth_first_search'>], reranker=<EdgeReranker.cross_encoder: 'cross_encoder'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3), node_config=NodeSearchConfig(search_methods=[<NodeSearchMethod.bm25: 'bm25'>, <NodeSearchMethod.cosine_similarity: 'cosine_similarity'>, <NodeSearchMethod.bfs: 'breadth_first_search'>], reranker=<NodeReranker.cross_encoder: 'cross_encoder'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3), episode_config=EpisodeSearchConfig(search_methods=[<EpisodeSearchMethod.bm25: 'bm25'>], reranker=<EpisodeReranker.cross_encoder: 'cross_encoder'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3), community_config=CommunitySearchConfig(search_methods=[<CommunitySearchMethod.bm25: 'bm25'>, <CommunitySearchMethod.cosine_similarity: 'cosine_similarity'>], reranker=<CommunityReranker.cross_encoder: 'cross_encoder'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3), limit=10, reranker_min_score=0), group_ids: list[str] | None = None, center_node_uuid: str | None = None, bfs_origin_node_uuids: list[str] | None = None, search_filter: graphiti_core.search.search_filters.SearchFilters | None = None, driver: graphiti_core.driver.driver.GraphDriver | None = None) -> graphiti_core.search.search_config.SearchResults

search docstring:

Perform a hybrid search on the knowledge graph.

This method executes a search query on the graph, combining vector and
text-based search techniques to retrieve relevant facts, returning the edges as a string.

This is our basic out-of-the-box search, for more robust results we recommend using our more advanced
search method graphiti.search_().

Parameters
----------
query : str
    The search query string.
center_node_uuid: str, optional
    Facts will be reranked based on proximity to this node
group_ids : list[str | None] | None, optional
    The graph partitions to return data from.
num_results : int, optional
    The maximum number of results to return. Defaults to 10.

Returns
-------
list
    A list of EntityEdge objects that are relevant to the search query.

Notes
-----
This method uses a SearchConfig with num_episodes set to 0 and
num_results set to the provided num_results parameter.

The search is performed using the current date and time as the reference
point for temporal relevance.
Update Todos

Inspect graphiti-core 0.29 search API + understand SearchResults shape

Examine queries.py to understand what nodes/facts the runtime needs

Patch queries.py to call graphiti-core 0.29's search_() returning nodes + edges

Update test mock surface in test_queries.py to match new call surface

Run full unit + smoke test suite to confirm no regression

Re-run Lilymay seed against live Synology FalkorDB

Verify Lilymay seed via mcp__graphiti__search_nodes / get_episodes

Create docs/research/ideas/phase-1-validation.md with held/drifted/falsified outline

Walk through end-to-end MCP demo session (Gate 3)
Bash Inspect SearchResults & node search recipes
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core.search.search_config import SearchResults, NodeSearchConfig, NodeReranker, NodeSearchMethod
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_NODE_DISTANCE,
    NODE_HYBRID_SEARCH_EPISODE_MENTIONS,
    EDGE_HYBRID_SEARCH_RRF,
)
print('SearchResults attrs:', [a for a in dir(SearchResults) if not a.startswith('_')])
print()
print('NODE_HYBRID_SEARCH_RRF:', NODE_HYBRID_SEARCH_RRF)
"

OUT
SearchResults attrs: ['construct', 'copy', 'dict', 'from_orm', 'json', 'merge', 'model_computed_fields', 'model_config', 'model_construct', 'model_copy', 'model_dump', 'model_dump_json', 'model_extra', 'model_fields', 'model_fields_set', 'model_json_schema', 'model_parametrized_name', 'model_post_init', 'model_rebuild', 'model_validate', 'model_validate_json', 'model_validate_strings', 'parse_file', 'parse_obj', 'parse_raw', 'schema', 'schema_json', 'update_forward_refs', 'validate']

NODE_HYBRID_SEARCH_RRF: edge_config=None node_config=NodeSearchConfig(search_methods=[<NodeSearchMethod.bm25: 'bm25'>, <NodeSearchMethod.cosine_similarity: 'cosine_similarity'>], reranker=<NodeReranker.rrf: 'reciprocal_rank_fusion'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3) episode_config=None community_config=None limit=10 reranker_min_score=0
Bash Inspect SearchResults fields
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core.search.search_config import SearchResults
print('SearchResults model_fields:')
for name, fld in SearchResults.model_fields.items():
    print(f'  {name}: {fld.annotation}')
"

OUT
SearchResults model_fields:
  edges: list[graphiti_core.edges.EntityEdge]
  edge_reranker_scores: list[float]
  nodes: list[graphiti_core.nodes.EntityNode]
  node_reranker_scores: list[float]
  episodes: list[graphiti_core.nodes.EpisodicNode]
  episode_reranker_scores: list[float]
  communities: list[graphiti_core.nodes.CommunityNode]
  community_reranker_scores: list[float]
Read queries.py (lines 2-101)
Bash Find all search call sites in queries.py
IN
grep -n "_build_student_state\|search_nodes\|search_memory_facts\|search(\|search_(" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py | head -30

OUT
4:holds the only call sites in Phase 1 that touch ``search_nodes`` /
5:``search_memory_facts`` directly. Every search call constructs
187:def _build_student_state(
332:                inner.search_nodes(group_ids, ""),
333:                inner.search_memory_facts(group_ids, ""),
349:    return _build_student_state(student_id, nodes, facts, stale_threshold_days)
Bash Find _build_student_state shape
IN
grep -n "_build_student_state\|node\.\|fact\.\|nodes:\|facts:" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py | head -40

OUT
187:def _build_student_state(
189:    nodes: Any,
190:    facts: Any,
349:    return _build_student_state(student_id, nodes, facts, stale_threshold_days)
Read queries.py (lines 161-290)
Read queries.py (lines 451-550)
Now let me look at get_topic_recommendations (line 352+) and the _inner_client helper.

Read queries.py (lines 131-165)
Read queries.py (lines 353-452)
Bash Inspect EntityNode/EntityEdge fields
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
print('EntityNode fields:')
for n,f in EntityNode.model_fields.items():
    print(f'  {n}: {f.annotation}')
print()
print('EntityEdge fields:')
for n,f in EntityEdge.model_fields.items():
    print(f'  {n}: {f.annotation}')
"

OUT
EntityNode fields:
  uuid: <class 'str'>
  name: <class 'str'>
  group_id: <class 'str'>
  labels: list[str]
  created_at: <class 'datetime.datetime'>
  name_embedding: list[float] | None
  summary: <class 'str'>
  attributes: dict[str, typing.Any]

EntityEdge fields:
  uuid: <class 'str'>
  group_id: <class 'str'>
  source_node_uuid: <class 'str'>
  target_node_uuid: <class 'str'>
  created_at: <class 'datetime.datetime'>
  name: <class 'str'>
  fact: <class 'str'>
  fact_embedding: list[float] | None
  episodes: list[str]
  expired_at: datetime.datetime | None
  valid_at: datetime.datetime | None
  invalid_at: datetime.datetime | None
  reference_time: datetime.datetime | None
  attributes: dict[str, typing.Any]
Bash Check entity definitions in student_model.py
IN
grep -n "Student\|Subject\|Text\|Topic\|AssessmentObjective\|TopicConfidence\|Misconception\|labels\|entity_type" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py | head -40

OUT
12:- ``Student`` — single learner identity (Phase 1 ships with Lilymay only).
13:- ``Subject`` — GCSE subject, e.g. AQA 8702 English Literature.
14:- ``Text`` — a literary text (primary, secondary, or context source).
15:- ``Topic`` — a revisable unit within a subject or text; carries AO refs.
16:- ``AssessmentObjective`` — AO1..AO6 with per-exam-board descriptions.
17:- ``Misconception`` — a documented misunderstanding observed in a session.
18:- ``TopicConfidence`` — per-student, per-topic confidence level + band.
22:- ``Student STUDIES Subject``
23:- ``Student WORKING_ON Text``
24:- ``Subject HAS_TEXT Text``
25:- ``Text COVERS Topic``
26:- ``Topic ASSESSED_BY AssessmentObjective``
27:- ``Student HAS_CONFIDENCE TopicConfidence`` — carries percentage + band.
76:#: Student STUDIES Subject — Lilymay's enrolled subjects.
79:#: Student WORKING_ON Text — the text currently being revised.
82:#: Subject HAS_TEXT Text — texts that fall under a subject's curriculum.
85:#: Text COVERS Topic — topics revisable from a given text.
88:#: Topic ASSESSED_BY AssessmentObjective — which AOs a topic exercises.
91:#: Student HAS_CONFIDENCE TopicConfidence — per-topic mastery state.
145:#: ``Text.kind`` discriminator: which corpus tier a text belongs to. Mirrors
148:TextKind = Literal["primary", "secondary", "context"]
151:class _StudentModelBase(BaseModel):
162:class Student(_StudentModelBase):
183:class Subject(_StudentModelBase):
200:class Text(_StudentModelBase):
204:    kind: TextKind = Field(
217:class Topic(_StudentModelBase):
220:    name: str = Field(..., description="Topic name, e.g. 'Witches Act 1'.")
223:        description="Reference to the parent Subject's spec_code or slug.",
228:            "Codes of AssessmentObjective entities this topic exercises "
234:class AssessmentObjective(_StudentModelBase):
252:class Misconception(_StudentModelBase):
261:        description="Topic name or slug this misconception attaches to.",
276:class TopicConfidence(_StudentModelBase):
281:        description="Student id this confidence belongs to.",
285:        description="Topic name or slug this confidence applies to.",
307:    "Student",
308:    "Subject",
309:    "Text",
310:    "Topic",
Bash Check how entities are written
IN
grep -n "add_episode\|EpisodeType\|entity_types\|Pydantic\|class Student\|class Subject\|class TopicConfidence" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py | head -30

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:1:"""Pydantic entity and relationship schema for the Graphiti student model.
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:142:# Entity classes (Pydantic v2 BaseModel subclasses)
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:152:    """Shared Pydantic configuration for all student-model entities.
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:162:class Student(_StudentModelBase):
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:183:class Subject(_StudentModelBase):
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:276:class TopicConfidence(_StudentModelBase):
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:13:- **Log-only failure**: a failed call to the underlying ``add_episode`` emits a
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:186:# name so the CC-13 single-call-site audit (``git grep -nE 'add_episode\s*\('
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:214:                ``add_episode``. May be ``None`` — in which case
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:255:        critically, it never ``await``\\ s the eventual ``add_episode`` call.
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:322:                # model_copy on Pydantic v2 produces a validated shallow copy.
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:373:        This is the **only** place ``add_episode`` is called anywhere in
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:382:            await self._client.add_episode(
Bash Inspect add_episode
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core import Graphiti
import inspect
sig = inspect.signature(Graphiti.add_episode)
print('add_episode params:')
for n,p in sig.parameters.items():
    print(f'  {n}: {p.annotation}')
"

OUT
add_episode params:
  self: <class 'inspect._empty'>
  name: <class 'str'>
  episode_body: <class 'str'>
  source_description: <class 'str'>
  reference_time: <class 'datetime.datetime'>
  source: <enum 'EpisodeType'>
  group_id: str | None
  uuid: str | None
  update_communities: <class 'bool'>
  entity_types: dict[str, type[pydantic.main.BaseModel]] | None
  excluded_entity_types: list[str] | None
  previous_episode_uuids: list[str] | None
  edge_types: dict[str, type[pydantic.main.BaseModel]] | None
  edge_type_map: dict[tuple[str, str], list[str]] | None
  custom_extraction_instructions: str | None
  saga: str | graphiti_core.nodes.SagaNode | None
  saga_previous_episode_uuid: str | None
Read async_write.py (lines 341-420)
Bash Inspect GraphitiClient wrapper
IN
grep -n "client_or_none\|class GraphitiClient\|def __init__\|def add_episode\|def search" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py | head -20

OUT
30:  ``close()``, and the ``client_or_none`` property. Domain operations such
136:class GraphitiClient:
141:    top of ``client_or_none`` by sibling modules (TASK-GSM-004 /
146:    def __init__(
155:    def client_or_none(self) -> Any | None:
228:        After the first call ``client_or_none`` returns ``None`` and any
Read async_write.py (lines 241-340)
Bash Inspect EpisodeBase
IN
grep -n "to_graphiti_episode_body\|source_description\|reference_time\|episode_kind\|class.*EpisodeBase\|class.*Episode" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/episodes.py | head -30

OUT
41:class EpisodeBase(BaseModel):
44:    Concrete subclasses pin ``episode_kind`` to a single literal and implement
45:    :meth:`to_graphiti_episode_body` to project the payload into the
54:    episode_kind: EpisodeKind
56:    def to_graphiti_episode_body(self) -> str:
64:            "Concrete episode subclasses must implement to_graphiti_episode_body()."
68:class SessionCompletedEpisode(EpisodeBase):
76:    episode_kind: Literal["session_completed"] = "session_completed"
87:    def to_graphiti_episode_body(self) -> str:
100:class TopicConfidenceUpdatedEpisode(EpisodeBase):
107:    episode_kind: Literal["topic_confidence_updated"] = "topic_confidence_updated"
117:    def to_graphiti_episode_body(self) -> str:
132:class MisconceptionObservedEpisode(EpisodeBase):
140:    episode_kind: Literal["misconception_observed"] = "misconception_observed"
148:    def to_graphiti_episode_body(self) -> str:
159:class SeedBaselineEpisode(EpisodeBase):
169:    episode_kind: Literal["seed_baseline"] = "seed_baseline"
180:    def to_graphiti_episode_body(self) -> str:
Read episodes.py (lines 2-81)
Bash Find by-group methods on nodes/edges
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge
print('EntityNode classmethods:')
for m in dir(EntityNode):
    if not m.startswith('_') and (m.startswith('get') or 'group' in m.lower() or 'list' in m.lower() or 'all' in m.lower()):
        print(f'  {m}')
print()
print('EpisodicNode classmethods:')
for m in dir(EpisodicNode):
    if not m.startswith('_') and (m.startswith('get') or 'group' in m.lower() or 'list' in m.lower() or 'all' in m.lower()):
        print(f'  {m}')
print()
print('EntityEdge classmethods:')
for m in dir(EntityEdge):
    if not m.startswith('_') and (m.startswith('get') or 'group' in m.lower() or 'list' in m.lower() or 'all' in m.lower()):
        print(f'  {m}')
"

OUT
EntityNode classmethods:
  delete_by_group_id
  get_by_group_ids
  get_by_uuid
  get_by_uuids

EpisodicNode classmethods:
  delete_by_group_id
  get_by_entity_node_uuid
  get_by_group_ids
  get_by_uuid
  get_by_uuids

EntityEdge classmethods:
  get_between_nodes
  get_by_group_ids
  get_by_node_uuid
  get_by_uuid
  get_by_uuids
Bash Inspect get_by_group_ids signatures
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
import inspect
print('EntityNode.get_by_group_ids:')
print(' ', inspect.signature(EntityNode.get_by_group_ids))
print()
print('EntityEdge.get_by_group_ids:')
print(' ', inspect.signature(EntityEdge.get_by_group_ids))
"

OUT
EntityNode.get_by_group_ids:
  (driver: graphiti_core.driver.driver.GraphDriver, group_ids: list[str], limit: int | None = None, uuid_cursor: str | None = None, with_embeddings: bool = False)

EntityEdge.get_by_group_ids:
  (driver: graphiti_core.driver.driver.GraphDriver, group_ids: list[str], limit: int | None = None, uuid_cursor: str | None = None, with_embeddings: bool = False)
Bash Confirm Graphiti exposes driver
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core import Graphiti
print('Graphiti instance attrs (driver-related):')
print(' ', [a for a in dir(Graphiti) if 'driver' in a.lower()])
"

OUT
Graphiti instance attrs (driver-related):
  []
Bash Look at Graphiti.__init__ to find driver attribute
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core import Graphiti
import inspect
src = inspect.getsource(Graphiti.__init__)
# print first 60 lines
print('\n'.join(src.splitlines()[:80]))
"

OUT
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        llm_client: LLMClient | None = None,
        embedder: EmbedderClient | None = None,
        cross_encoder: CrossEncoderClient | None = None,
        store_raw_episode_content: bool = True,
        graph_driver: GraphDriver | None = None,
        max_coroutines: int | None = None,
        tracer: Tracer | None = None,
        trace_span_prefix: str = 'graphiti',
    ):
        """
        Initialize a Graphiti instance.

        This constructor sets up a connection to a graph database and initializes
        the LLM client for natural language processing tasks.

        Parameters
        ----------
        uri : str
            The URI of the Neo4j database.
        user : str
            The username for authenticating with the Neo4j database.
        password : str
            The password for authenticating with the Neo4j database.
        llm_client : LLMClient | None, optional
            An instance of LLMClient for natural language processing tasks.
            If not provided, a default OpenAIClient will be initialized.
        embedder : EmbedderClient | None, optional
            An instance of EmbedderClient for embedding tasks.
            If not provided, a default OpenAIEmbedder will be initialized.
        cross_encoder : CrossEncoderClient | None, optional
            An instance of CrossEncoderClient for reranking tasks.
            If not provided, a default OpenAIRerankerClient will be initialized.
        store_raw_episode_content : bool, optional
            Whether to store the raw content of episodes. Defaults to True.
        graph_driver : GraphDriver | None, optional
            An instance of GraphDriver for database operations.
            If not provided, a default Neo4jDriver will be initialized.
        max_coroutines : int | None, optional
            The maximum number of concurrent operations allowed. Overrides SEMAPHORE_LIMIT set in the environment.
            If not set, the Graphiti default is used.
        tracer : Tracer | None, optional
            An OpenTelemetry tracer instance for distributed tracing. If not provided, tracing is disabled (no-op).
        trace_span_prefix : str, optional
            Prefix to prepend to all span names. Defaults to 'graphiti'.

        Returns
        -------
        None

        Notes
        -----
        This method establishes a connection to a graph database (Neo4j by default) using the provided
        credentials. It also sets up the LLM client, either using the provided client
        or by creating a default OpenAIClient.

        The default database name is defined during the driver’s construction. If a different database name
        is required, it should be specified in the URI or set separately after
        initialization.

        The OpenAI API key is expected to be set in the environment variables.
        Make sure to set the OPENAI_API_KEY environment variable before initializing
        Graphiti if you're using the default OpenAIClient.
        """

        if graph_driver:
            self.driver = graph_driver
        else:
            if uri is None:
                raise ValueError('uri must be provided when graph_driver is None')
            self.driver = Neo4jDriver(uri, user, password)

        self.store_raw_episode_content = store_raw_episode_content
        self.max_coroutines = max_coroutines
        if llm_client:
            self.llm_client = llm_client
Read test_queries.py (lines 2-121)
Bash Locate all search refs in test
IN
grep -n "search_nodes\|search_memory_facts\|search_(" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_queries.py

OUT
8:  ``event=student_state_read_timeout`` (mocked slow ``search_nodes``).
75:        self.search_nodes_calls: list[dict[str, Any]] = []
76:        self.search_memory_facts_calls: list[dict[str, Any]] = []
78:    async def search_nodes(self, group_ids: list[str], query: str) -> list[Any]:
79:        self.search_nodes_calls.append({"group_ids": group_ids, "query": query})
84:    async def search_memory_facts(
87:        self.search_memory_facts_calls.append(
193:    assert inner.search_nodes_calls[0]["group_ids"] == expected_group_ids
194:    assert inner.search_memory_facts_calls[0]["group_ids"] == expected_group_ids
464:    search_methods = {"search_nodes", "search_memory_facts"}
Read test_queries.py (lines 441-520)
Read test_queries.py (lines 171-230)
Bash Find add_episode mock in async_write tests
IN
grep -n "add_episode\|class.*Mock\|async def add_episode\|def add_episode" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_async_write.py | head -25

OUT
7:  underlying ``add_episode`` would hang for 80s+
14:- CC-13 conformance: ``add_episode(`` appears in exactly one src/ file
55:    """Minimal duck-typed Graphiti client recording every ``add_episode`` call."""
61:    async def add_episode(self, *args: Any, **kwargs: Any) -> Any:
156:        # The single add_episode call carries the expected kwargs.
189:# AC: <50ms dispatcher even when add_episode hangs
401:        assert client.calls == []  # no add_episode call made
511:# CC-13 conformance: single ``add_episode(`` call site in src/
516:    def test_add_episode_appears_exactly_once_in_src(self) -> None:
520:        pattern = re.compile(r"add_episode\s*\(")
529:            "CC-13 violation: add_episode( found at "
533:            f"add_episode( appeared outside async_write.py: {matches}"
Bash Check seeder write path
IN
grep -rn "schedule_write\|GraphitiWriteHelper" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py | head -10

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:37:  :meth:`~study_tutor.knowledge.async_write.GraphitiWriteHelper.schedule_write`
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:70:from study_tutor.knowledge.async_write import GraphitiWriteHelper
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:374:# Per-entity seed writers — every one routes through helper.schedule_write
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:391:def _seed_student(helper: GraphitiWriteHelper, *, now: datetime) -> None:
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:393:    helper.schedule_write(
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:409:def _seed_subjects(helper: GraphitiWriteHelper) -> None:
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:412:        helper.schedule_write(
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:426:def _seed_texts(helper: GraphitiWriteHelper) -> None:
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:429:        helper.schedule_write(
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:444:def _seed_assessment_objectives(helper: GraphitiWriteHelper) -> None:
Bash Read add_episode source signature
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core import Graphiti
import inspect
src = inspect.getsource(Graphiti.add_episode)
print('\n'.join(src.splitlines()[:25]))
" 2>&1

OUT
    async def add_episode(
        self,
        name: str,
        episode_body: str,
        source_description: str,
        reference_time: datetime,
        source: EpisodeType = EpisodeType.message,
        group_id: str | None = None,
        uuid: str | None = None,
        update_communities: bool = False,
        entity_types: dict[str, type[BaseModel]] | None = None,
        excluded_entity_types: list[str] | None = None,
        previous_episode_uuids: list[str] | None = None,
        edge_types: dict[str, type[BaseModel]] | None = None,
        edge_type_map: dict[tuple[str, str], list[str]] | None = None,
        custom_extraction_instructions: str | None = None,
        saga: str | SagaNode | None = None,
        saga_previous_episode_uuid: str | None = None,
    ) -> AddEpisodeResults:
        """
        Process an episode and update the graph.

        This method extracts information from the episode, creates nodes and edges,
        and updates the graph database accordingly.
Found a second broken site: async_write.py:382-387 calls add_episode(group_ids=..., flush_id=...) but graphiti-core 0.29's add_episode takes group_id (singular) and has no flush_id param. So write-path is broken too — re-seeding without fixing this would TypeError. Tests pass because the mock swallows **kwargs.

Adjusting scope: fix both read AND write in this Path B sweep. Proceeding.

Update Todos

Inspect graphiti-core 0.29 search API + understand SearchResults shape

Examine queries.py + async_write.py + seed script to map all broken call sites

Patch queries.py read path: EntityNode/EntityEdge.get_by_group_ids on driver

Patch async_write.py write path: add_episode signature fix (group_id, source, source_description, reference_time)

Update test_queries.py mock to expose driver seam; update AST lint for new call shape

Update test_async_write.py if any kwargs assertions break

Run full unit + smoke test suite to confirm no regression

Re-run Lilymay seed against live Synology FalkorDB

Verify Lilymay seed via mcp__graphiti__search_nodes / get_episodes

Create docs/research/ideas/phase-1-validation.md with held/drifted/falsified outline

Walk through end-to-end MCP demo session (Gate 3)
Patching queries.py read path
Edit queries.py
Added 8 lines
Edit queries.py
Added 5 lines
Now extend _entity_type to handle graphiti-core's labels: list[str] and replace the broken search calls.

Edit queries.py
Added 13 lines
Now replace the broken search_nodes/search_memory_facts block with the new partition reader.

Edit queries.py
Added 41 lines
Now wire get_student_state to call the new seam.

Edit queries.py
Removed 3 lines
Now patch _build_student_state to recognize edges by name (graphiti-core's EntityEdge.name carries the relationship type).

Read queries.py (lines 286-310)
_build_student_state already falls back to _attr(fact, "name") so EntityEdge.name is covered. Now patching async_write.py.

Read async_write.py (lines 2-61)
Edit async_write.py
Added 1 line
Edit async_write.py
Added 9 lines
Now add the _add_episode_kwargs helper near the top of the module so the call shape is testable in isolation.

Read async_write.py (lines 101-140)
Read async_write.py (lines 141-175)
Edit async_write.py
Added 29 lines
Bash Find seed idempotency check
IN
grep -n "_already_seeded\|already_seeded\|state\." /Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py | head -25

OUT
513:def _is_already_seeded(state: Any) -> bool:
525:    if state.subjects:
527:    if state.topic_confidences:
529:    if state.year_group is not None:
550:    if _is_already_seeded(state):
555:                "reason": "already_seeded",
601:            len(final_state.subjects),
602:            len(final_state.topic_confidences),
607:                "subjects": len(final_state.subjects),
608:                "topic_confidences": len(final_state.topic_confidences),
Read seed_student_model.py (lines 535-634)
Update Todos

Inspect graphiti-core 0.29 search API + understand SearchResults shape

Examine queries.py + async_write.py + seed script to map all broken call sites

Patch queries.py read path: EntityNode/EntityEdge.get_by_group_ids on driver

Patch async_write.py write path: add_episode signature fix (group_id, source, source_description, reference_time)

Update test_queries.py mock to expose driver seam; update AST lint for new call shape

Update test_async_write.py if any kwargs assertions break

Run full unit + smoke test suite to confirm no regression

Re-run Lilymay seed against live Synology FalkorDB

Verify Lilymay seed via mcp__graphiti__search_nodes / get_episodes

Create docs/research/ideas/phase-1-validation.md with held/drifted/falsified outline

Walk through end-to-end MCP demo session (Gate 3)
The seam I added in _read_student_partition recognizes the legacy search_nodes/search_memory_facts duck-type, so existing test mocks still work. Let me run the test suite to see what (if anything) actually breaks.

Bash Run queries + async_write unit tests
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m pytest tests/unit/knowledge/test_queries.py tests/unit/knowledge/test_async_write.py -q --no-header 2>&1 | tail -30

OUT
        # Walk the worktree's src/ tree relative to this test file's location.
        src_root = Path(__file__).resolve().parents[3] / "src"
        assert src_root.exists(), f"src tree not found at {src_root}"
        pattern = re.compile(r"add_episode\s*\(")
        matches: list[tuple[str, int]] = []
        for path in src_root.rglob("*.py"):
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if pattern.search(line):
                    matches.append((str(path), lineno))
>       assert len(matches) == 1, (
            "CC-13 violation: add_episode( found at "
            f"{len(matches)} call sites: {matches}"
        )
E       AssertionError: CC-13 violation: add_episode( found at 2 call sites: [('/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py', 165), ('/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py', 426)]
E       assert 2 == 1
E        +  where 2 = len([('/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py', 165), ('/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py', 426)])

tests/unit/knowledge/test_async_write.py:528: AssertionError
=============================== warnings summary ===============================
tests/unit/knowledge/test_async_write.py::TestScheduleWriteValid::test_returns_asyncio_task
  /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/search_interface/search_interface.py:22: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class SearchInterface(BaseModel):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/unit/knowledge/test_async_write.py::TestScheduleWriteValid::test_returns_asyncio_task
FAILED tests/unit/knowledge/test_async_write.py::TestCC13SingleCallSite::test_add_episode_appears_exactly_once_in_src
2 failed, 47 passed, 1 warning in 3.47s
Bash Inspect both add_episode hits
IN
sed -n '160,170p;420,430p' /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py

OUT
    group_id: str | None,
) -> dict[str, Any]:
    """Build the kwargs dict for graphiti-core 0.29's ``add_episode``.

    Hoisted out so :meth:`GraphitiWriteHelper._perform_write` stays
    auditable (CC-13: a single ``add_episode(...)`` call site in src/)
    and so tests can assert on the call shape without instantiating a
    helper. ``flush_id`` rides in ``source_description`` rather than as
    a first-class parameter because graphiti-core has no flush-id slot;
    keeping it greppable here preserves the audit-trail property the
    structured logs already rely on.
                name=episode_kind,
                episode_body=body,
                flush_id=flush_id,
                group_id=primary_group_id,
            )
            # === The single CC-13-protected call site ===
            await self._client.add_episode(**kwargs)
        except BaseException as exc:  # noqa: BLE001 -- log-only failure required by ADR-ARCH-019
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "graphiti write failed",
Edit async_write.py
Modified
Bash Inspect single failing schedule_write test
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m pytest tests/unit/knowledge/test_async_write.py::TestScheduleWriteValid::test_returns_asyncio_task -q --no-header 2>&1 | tail -50

OUT
F                                                                        [100%]
=================================== FAILURES ===================================
_______________ TestScheduleWriteValid.test_returns_asyncio_task _______________

self = <knowledge.test_async_write.TestScheduleWriteValid object at 0x104af5e50>
valid_groups = ['student:lilymay']

    @pytest.mark.asyncio
    async def test_returns_asyncio_task(self, valid_groups: list[str]) -> None:
        client = FakeClient()
        helper = GraphitiWriteHelper(client=client)
        task = helper.schedule_write(valid_groups, make_session_episode(), "F3")
        assert task is not None
        assert isinstance(task, asyncio.Task)
        await task
        assert len(client.calls) == 1
        # The single add_episode call carries the expected kwargs.
        _args, kwargs = client.calls[0]
        assert kwargs["name"] == "session_completed"
>       assert kwargs["flush_id"] == "F3"
               ^^^^^^^^^^^^^^^^^^
E       KeyError: 'flush_id'

tests/unit/knowledge/test_async_write.py:159: KeyError
=============================== warnings summary ===============================
tests/unit/knowledge/test_async_write.py::TestScheduleWriteValid::test_returns_asyncio_task
  /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/search_interface/search_interface.py:22: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class SearchInterface(BaseModel):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/unit/knowledge/test_async_write.py::TestScheduleWriteValid::test_returns_asyncio_task
1 failed, 1 warning in 0.35s
Read test_async_write.py (lines 131-180)
Bash Find all flush_id / group_ids kwarg assertions
IN
grep -n "flush_id\|group_ids\b\|kwargs\[" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_async_write.py | head -40

OUT
158:        assert kwargs["name"] == "session_completed"
159:        assert kwargs["flush_id"] == "F3"
160:        assert kwargs["group_ids"] == valid_groups
161:        assert "Student lilymay completed session sess-001" in kwargs["episode_body"]
352:    def test_invalid_flush_id_rejected(
Edit test_async_write.py
Added 5 lines
Bash Re-run queries + async_write tests
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m pytest tests/unit/knowledge/test_queries.py tests/unit/knowledge/test_async_write.py -q --no-header 2>&1 | tail -8

OUT
.................................................                        [100%]
=============================== warnings summary ===============================
tests/unit/knowledge/test_async_write.py::TestScheduleWriteValid::test_returns_asyncio_task
  /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/search_interface/search_interface.py:22: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class SearchInterface(BaseModel):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
49 passed, 1 warning in 3.44s
All 49 queries+async_write tests pass. Now full unit + smoke run.

Bash Full unit+smoke+integration run
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m pytest tests/unit tests/smoke tests/integration -q --no-header 2>&1 | tail -10

OUT
tests/unit/planner/test_protocols.py:164: AssertionError
=============================== warnings summary ===============================
tests/unit/knowledge/test_async_write.py::TestScheduleWriteValid::test_returns_asyncio_task
  /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/search_interface/search_interface.py:22: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class SearchInterface(BaseModel):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/unit/planner/test_protocols.py::test_mypy_strict_accepts_structurally_conforming_rule
1 failed, 695 passed, 1 warning in 25.88s
695/696 pass — the only failure is the pre-existing mypy-on-system-Python env issue from earlier, not introduced by my patches. Let me update todos and run the seeder.

Update Todos

Inspect graphiti-core 0.29 search API + understand SearchResults shape

Examine queries.py + async_write.py + seed script to map all broken call sites

Patch queries.py read path: EntityNode/EntityEdge.get_by_group_ids on driver

Patch async_write.py write path: add_episode signature fix (group_id, source, source_description, reference_time)

Update test_queries.py mock to expose driver seam; update AST lint for new call shape

Update test_async_write.py if any kwargs assertions break

Run full unit + smoke test suite to confirm no regression

Re-run Lilymay seed against live Synology FalkorDB

Verify Lilymay seed via mcp__graphiti__search_nodes / get_episodes

Create docs/research/ideas/phase-1-validation.md with held/drifted/falsified outline

Walk through end-to-end MCP demo session (Gate 3)
Bash Run Lilymay seed (post-patch)
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m dotenv -f .env run -- /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python scripts/seed_student_model.py 2>&1 | tail -80

OUT
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 114, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 84, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/client.py", line 781, in execute_command
    result = await conn.retry.call_with_retry(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<5 lines>...
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/retry.py", line 81, in call_with_retry
    raise error
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/retry.py", line 69, in call_with_retry
    return await do()
           ^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/client.py", line 722, in _send_command_parse_response
    return await self.parse_response(conn, command_name, **options)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/client.py", line 823, in parse_response
    response = await connection.read_response()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/connection.py", line 734, in read_response
    response = await self._parser.read_response(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        disable_decoding=disable_decoding
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/resp2.py", line 82, in read_response
    response = await self._read_response(disable_decoding=disable_decoding)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/resp2.py", line 90, in _read_response
    raw = await self._readline()
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/base.py", line 561, in _readline
    raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
redis.exceptions.ConnectionError: Connection closed by server.
2026-05-02 07:36:01,023 ERROR study_tutor.seed: seeding failed with unhandled exception
Traceback (most recent call last):
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py", line 651, in <module>
    sys.exit(asyncio.run(main()))
             ~~~~~~~~~~~^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/runners.py", line 204, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/runners.py", line 127, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 719, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py", line 634, in main
    return await seed_lilymay(client, helper)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py", line 549, in seed_lilymay
    state = await get_student_state(client, STUDENT_ID)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py", line 397, in get_student_state
    nodes, facts = await asyncio.wait_for(
                   ^^^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
    )
    ^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py", line 488, in wait_for
    return await fut
           ^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py", line 203, in _read_student_partition
    nodes, edges = await asyncio.gather(
                   ^^^^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/edges.py", line 539, in get_by_group_ids
    raise GroupsEdgesNotFoundError(group_ids)
graphiti_core.errors.GroupsEdgesNotFoundError: no edges found for group ids ['student:lilymay']
graphiti-core 0.29 raises GroupsEdgesNotFoundError instead of returning [] when the partition is empty. Need to swallow that as the bootstrap case.

Bash Find all NotFound errors
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
from graphiti_core.errors import GroupsEdgesNotFoundError
print('GroupsEdgesNotFoundError:', GroupsEdgesNotFoundError)
import graphiti_core.errors as e
print('Available errors:', [n for n in dir(e) if 'NotFound' in n or 'Group' in n])
"

OUT
GroupsEdgesNotFoundError: <class 'graphiti_core.errors.GroupsEdgesNotFoundError'>
Available errors: ['EdgeNotFoundError', 'EdgesNotFoundError', 'GroupIdValidationError', 'GroupsEdgesNotFoundError', 'GroupsNodesNotFoundError', 'NodeNotFoundError']
Edit queries.py
Added 23 lines
Bash Re-run queries tests after empty-partition handling
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m pytest tests/unit/knowledge/test_queries.py -q --no-header 2>&1 | tail -6

OUT
............                                                             [100%]
12 passed in 0.08s
Now re-run the seed.

Bash Run Lilymay seed (post-empty-partition fix)
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m dotenv -f .env run -- /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python scripts/seed_student_model.py 2>&1 | tail -50

OUT
2026-05-02 07:36:31,459 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: Connection closed by server.
CREATE INDEX FOR ()-[e:NEXT_EPISODE]-() ON (e.uuid, e.group_id)
{}
2026-05-02 07:36:31,459 ERROR asyncio: Task exception was never retrieved
future: <Task finished name='Task-2' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=network:ConnectionError>
Traceback (most recent call last):
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 114, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 84, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/client.py", line 781, in execute_command
    result = await conn.retry.call_with_retry(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<5 lines>...
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/retry.py", line 81, in call_with_retry
    raise error
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/retry.py", line 69, in call_with_retry
    return await do()
           ^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/client.py", line 722, in _send_command_parse_response
    return await self.parse_response(conn, command_name, **options)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/client.py", line 823, in parse_response
    response = await connection.read_response()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/connection.py", line 734, in read_response
    response = await self._parser.read_response(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        disable_decoding=disable_decoding
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/resp2.py", line 82, in read_response
    response = await self._read_response(disable_decoding=disable_decoding)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/resp2.py", line 90, in _read_response
    raw = await self._readline()
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/base.py", line 561, in _readline
    raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
redis.exceptions.ConnectionError: Connection closed by server.
Bash Re-run seed and capture full log
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m dotenv -f .env run -- /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python scripts/seed_student_model.py > /tmp/seed_run.log 2>&1; echo "exit code: $?"; head -40 /tmp/seed_run.log; echo "--- ... ---"; tail -10 /tmp/seed_run.log

OUT
exit code: 0
2026-05-02 07:36:41,096 INFO study_tutor.knowledge.graphiti_client: graphiti client ready in 552ms
2026-05-02 07:36:41,096 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-02 07:36:41,098 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-02 07:36:41,099 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-02 07:36:41,101 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-02 07:36:41,103 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-02 07:36:41,104 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-02 07:36:41,105 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:36:41,106 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:36:41,106 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:36:41,106 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:36:41,106 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:36:41,106 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:36:41,106 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:36:41,106 WARNING study_tutor.knowledge.async_write: graphiti write failed
--- ... ---
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/resp2.py", line 82, in read_response
    response = await self._read_response(disable_decoding=disable_decoding)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/resp2.py", line 90, in _read_response
    raw = await self._readline()
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/base.py", line 561, in _readline
    raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
redis.exceptions.ConnectionError: Connection closed by server.
Bash Extract key events from seed log
IN
grep -E "INFO|WARNING|ERROR|seeding_completed|seeding_verification_warning|graphiti_write_succeeded|graphiti_write_failed|seeding_pending" /tmp/seed_run.log | grep -v "Index already exists\|graphiti write scheduled\|graphiti write failed\|Task exception\|asyncio.Task" | head -40

OUT
2026-05-02 07:36:41,096 INFO study_tutor.knowledge.graphiti_client: graphiti client ready in 552ms
2026-05-02 07:36:41,109 INFO study_tutor.seed: seeded Lilymay baseline (subjects=0, confidences=0, succeeded_writes=25)
2026-05-02 07:36:41,109 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: Connection closed by server.
    raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
Bash Count scheduled vs succeeded vs failed
IN
grep -c "graphiti write scheduled\|graphiti write succeeded\|graphiti write failed" /tmp/seed_run.log

OUT
50
Bash Look for failure error class detail
IN
grep "error_class" /tmp/seed_run.log | head -3

OUT
(Bash completed with no output)
Bash Count scheduled/succeeded/failed
IN
echo "scheduled: $(grep -c 'graphiti write scheduled' /tmp/seed_run.log)"; echo "succeeded: $(grep -c 'graphiti write succeeded' /tmp/seed_run.log)"; echo "failed: $(grep -c 'graphiti write failed' /tmp/seed_run.log)"

OUT
scheduled: 25
succeeded: 0
failed: 25
Bash Probe single add_episode against live FalkorDB
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
import asyncio, logging, os
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')
import dotenv; dotenv.load_dotenv('.env')
from study_tutor.knowledge.graphiti_client import GraphitiConnectionConfig, get_client
from datetime import datetime, timezone
from graphiti_core.nodes import EpisodeType

async def main():
    cfg = GraphitiConnectionConfig(
        falkor_host='whitestocks', falkor_port=6379, database='study_tutor',
        llm_provider='gemini', llm_model='gemini-2.5-pro',
        embedder_url='http://promaxgb10-41b1:8001/v1', timeout_seconds=5.0,
    )
    client = await get_client(cfg)
    inner = client.client_or_none
    print('client ready')
    try:
        result = await inner.add_episode(
            name='probe',
            episode_body='Lilymay studies AQA 8702 English Literature.',
            source=EpisodeType.text,
            source_description='probe',
            reference_time=datetime.now(timezone.utc),
            group_id='student:lilymay',
        )
        print('OK:', type(result).__name__)
    except Exception as e:
        print('ERR:', type(e).__name__, str(e)[:300])
    finally:
        await client.close()

asyncio.run(main())
" 2>&1 | tail -20

OUT
    response = await connection.read_response()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/asyncio/connection.py", line 734, in read_response
    response = await self._parser.read_response(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        disable_decoding=disable_decoding
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/resp2.py", line 82, in read_response
    response = await self._read_response(disable_decoding=disable_decoding)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/resp2.py", line 90, in _read_response
    raw = await self._readline()
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/redis/_parsers/base.py", line 561, in _readline
    raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
redis.exceptions.ConnectionError: Connection closed by server.
client ready
ERR: GroupIdValidationError group_id "student:lilymay" must contain only alphanumeric characters, dashes, or underscores
The real culprit surfaces: graphiti-core 0.29 rejects colons in group_id (GroupIdValidationError: ... must contain only alphanumeric characters, dashes, or underscores). The Phase 1 group-id discipline (student:lilymay, subject:<slug>, fleet:appmilla) is incompatible.

Bash Find prefix constants usage
IN
grep -rn "STUDENT_GROUP_PREFIX\|SUBJECT_GROUP_PREFIX\|FLEET_GROUP_ID" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src /Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts 2>/dev/null | head -20

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/tutoring/session_end.py:53:from study_tutor.knowledge.student_model import STUDENT_GROUP_PREFIX
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/tutoring/session_end.py:516:        group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:44:    FLEET_GROUP_ID,
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:45:    STUDENT_GROUP_PREFIX,
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:46:    SUBJECT_GROUP_PREFIX,
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:145:            not gid.startswith(STUDENT_GROUP_PREFIX)
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:146:            and not gid.startswith(SUBJECT_GROUP_PREFIX)
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/async_write.py:147:            and gid != FLEET_GROUP_ID
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:58:STUDENT_GROUP_PREFIX: str = "student:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:62:SUBJECT_GROUP_PREFIX: str = "subject:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:69:FLEET_GROUP_ID: str = "fleet:appmilla"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:322:    "STUDENT_GROUP_PREFIX",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:323:    "SUBJECT_GROUP_PREFIX",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:324:    "FLEET_GROUP_ID",
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:45:    STUDENT_GROUP_PREFIX,
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:417:    group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/queries.py:577:    group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:82:    FLEET_GROUP_ID,
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:83:    STUDENT_GROUP_PREFIX,
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:84:    SUBJECT_GROUP_PREFIX,
Bash Count colon-form group-id literals
IN
grep -rn '"student:\|"subject:\|"fleet:' /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests /Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts 2>/dev/null | wc -l

OUT
      18
Bash List colon-form group-id literals
IN
grep -rn '"student:\|"subject:\|"fleet:' /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests /Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts 2>/dev/null

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:58:STUDENT_GROUP_PREFIX: str = "student:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:62:SUBJECT_GROUP_PREFIX: str = "subject:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/student_model.py:69:FLEET_GROUP_ID: str = "fleet:appmilla"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/tutoring/test_session_end.py:264:        assert kwargs["group_ids"] == ["student:lilymay"]
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/tutoring/test_session_end.py:412:            group_ids=["student:lilymay"],
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/tutoring/test_session_end.py:582:                group_ids=["student:lilymay"], episode=episode, flush_id="F1"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/tutoring/test_session_end.py:612:            group_ids=["student:lilymay"], episode=episode, flush_id="F1"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_graphiti_client.py:478:    assert STUDENT_GROUP_PREFIX == "student:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_graphiti_client.py:479:    assert SUBJECT_GROUP_PREFIX == "subject:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_graphiti_client.py:480:    assert FLEET_GROUP_ID == "fleet:appmilla"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_async_write.py:332:            "fleet:not-appmilla",  # wrong fleet constant
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_student_model.py:309:    assert STUDENT_GROUP_PREFIX == "student:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_student_model.py:310:    assert SUBJECT_GROUP_PREFIX == "subject:"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_student_model.py:311:    assert FLEET_GROUP_ID == "fleet:appmilla"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_student_model.py:321:    assert f"{STUDENT_GROUP_PREFIX}lilymay" == "student:lilymay"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_student_model.py:322:    assert f"{SUBJECT_GROUP_PREFIX}gcse-english" == "subject:gcse-english"
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/knowledge/test_student_model.py:371:    assert "fleet:appmilla" in docstring
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/seed_student_model.py:54:    search_nodes(query="Lilymay", group_ids=["student:lilymay"])
Read student_model.py (lines 51-75)
Edit student_model.py
Added 8 lines
Now update the tests that assert the colon form.

Read test_student_model.py (lines 301-385)
Edit test_student_model.py
Added 3 lines
Edit test_student_model.py
Modified
Edit test_student_model.py
Added 3 lines
Now check student_model.py's module docstring for the cross-repo divergence text.

Read student_model.py (lines 2-51)
Edit student_model.py
Added 4 lines
Now update the other tests with bare colon literals.

Read test_session_end.py (lines 259-268)
Read test_session_end.py (lines 406-420)
Read test_session_end.py (lines 576-620)
Bash Replace bare colon literals across tests
IN
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
import re, pathlib
files = [
    'tests/unit/tutoring/test_session_end.py',
    'tests/unit/knowledge/test_async_write.py',
]
for fp in files:
    p = pathlib.Path('/Users/richardwoollcott/Projects/appmilla_github/study-tutor') / fp
    src = p.read_text()
    new = src.replace('\"student:lilymay\"', '\"student-lilymay\"')
    new = new.replace('\"fleet:not-appmilla\"', '\"fleet-not-appmilla\"')
    if new != src:
        p.write_text(new)
        print(f'updated {fp}: -{src.count(chr(34) + chr(34))} ...')
    print(fp, 'colons remaining:', len(re.findall(r'\"(student|subject|fleet):', new)))
"

OUT
updated tests/unit/tutoring/test_session_end.py: -35 ...
tests/unit/tutoring/test_session_end.py colons remaining: 0
updated tests/unit/knowledge/test_async_write.py: -9 ...
tests/unit/knowledge/test_async_write.py colons remaining: 0
Read test_graphiti_client.py (lines 473-487)
Edit test_graphiti_client.py
Added 2 lines
Read seed_student_model.py (lines 51-60)
Edit seed_student_model.py
Modified
Now also check the graphiti MCP server's group-id used by the Graphiti MCP — it might use a different config. Let me re-run tests, then probe the seeder.

Bash Re-run full suite (excluding env-issue mypy test)
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m pytest tests/unit tests/smoke tests/integration -q --no-header --ignore=tests/unit/planner/test_protocols.py 2>&1 | tail -10

OUT
........................................................................ [ 86%]
........................................................................ [ 97%]
...................                                                      [100%]
=============================== warnings summary ===============================
tests/unit/knowledge/test_async_write.py::TestScheduleWriteValid::test_returns_asyncio_task
  /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/driver/search_interface/search_interface.py:22: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class SearchInterface(BaseModel):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
667 passed, 1 warning in 17.74s
All 667 tests green. Now re-running the seed.

Bash Re-run seed and surface summary
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -m dotenv -f .env run -- /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python scripts/seed_student_model.py > /tmp/seed_run2.log 2>&1; echo "exit code: $?"; echo "---summary---"; grep -E "seeding_completed|seeded|seeding_skipped|seeding_failed|seeding_verification|graphiti write succeeded|graphiti write failed" /tmp/seed_run2.log | grep -v "asyncio.Task\|Traceback" | head -20; echo "---counts---"; echo "scheduled: $(grep -c 'graphiti write scheduled' /tmp/seed_run2.log) / succeeded: $(grep -c 'graphiti write succeeded' /tmp/seed_run2.log) / failed: $(grep -c 'graphiti write failed' /tmp/seed_run2.log)"

OUT
exit code: 0
---summary---
2026-05-02 07:39:52,834 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,870 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,871 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,874 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,894 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,895 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,906 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,910 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,914 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,918 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,934 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,938 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,938 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,947 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,950 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,954 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,955 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,956 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,958 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-02 07:39:52,962 WARNING study_tutor.knowledge.async_write: graphiti write failed
---counts---
scheduled: 25 / succeeded: 0 / failed: 25
Bash Probe single add_episode with dash group_id
IN
PATH="/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin:$PATH" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "
import asyncio, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')
import dotenv; dotenv.load_dotenv('.env')
from study_tutor.knowledge.graphiti_client import GraphitiConnectionConfig, get_client
from datetime import datetime, timezone
from graphiti_core.nodes import EpisodeType

async def main():
    cfg = GraphitiConnectionConfig(
        falkor_host='whitestocks', falkor_port=6379, database='study_tutor',
        llm_provider='gemini', llm_model='gemini-2.5-pro',
        embedder_url='http://promaxgb10-41b1:8001/v1', timeout_seconds=5.0,
    )
    client = await get_client(cfg)
    inner = client.client_or_none
    print('client ready')
    try:
        result = await inner.add_episode(
            name='probe',
            episode_body='Lilymay studies AQA 8702 English Literature.',
            source=EpisodeType.text,
            source_description='probe',
            reference_time=datetime.now(timezone.utc),
            group_id='student-lilymay',
        )
        print('OK:', type(result).__name__)
    except Exception as e:
        import traceback; traceback.print_exc()
    finally:
        await client.close()

asyncio.run(main())
" 2>&1 | tail -30

OUT
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/llm_client/openai_base_client.py", line 245, in generate_response
    response, input_tokens, output_tokens = await self._generate_response(
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        messages, response_model, max_tokens, model_size
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/llm_client/openai_base_client.py", line 172, in _generate_response
    response = await self._create_structured_completion(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<7 lines>...
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/graphiti_core/llm_client/openai_client.py", line 99, in _create_structured_completion
    response = await self.client.responses.parse(**request_kwargs)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/openai/resources/responses/responses.py", line 2916, in parse
    return await self._post(
           ^^^^^^^^^^^^^^^^^
    ...<46 lines>...
    )
    ^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/openai/_base_client.py", line 1913, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/lib/python3.14/site-packages/openai/_base_client.py", line 1698, in request
    raise self._make_status_error_from_response(err.response) from None
openai.AuthenticationError: Error code: 401 - {'error': {'message': 'Incorrect API key provided: not_needed. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'param': None, 'code': 'invalid_api_key'}}
client ready
Read graphiti_client.py (lines 116-195)
Bash Find how Graphiti is constructed
IN
grep -n "def get_client\|llm_client\|embedder\|cross_encoder\|Graphiti(" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py | head -20

OUT
27:  FalkorDB host/port/database, LLM provider/model, embedder URL, and
71:        embedder_url: HTTP URL of the local embedder service (GB10:8001).
83:    embedder_url: str = Field(min_length=1)
262:async def get_client(
Read graphiti_client.py (lines 241-320)
Bash Check for Gemini wiring + library availability
IN
grep -rn "GeminiClient\|GeminiEmbedder\|GeminiLLM\|llm_provider" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/src 2>/dev/null | head -10; echo "---"; /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "from graphiti_core.llm_client import GeminiClient; print('GeminiClient ok')" 2>&1 | head -3

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:68:        llm_provider: Backing LLM provider for graphiti-core (default
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/src/study_tutor/knowledge/graphiti_client.py:81:    llm_provider: str = "gemini"
---
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    from graphiti_core.llm_client import GeminiClient; print('GeminiClient ok')
Update Todos

Inspect graphiti-core 0.29 search API + understand SearchResults shape

Examine queries.py + async_write.py + seed script to map all broken call sites

Patch queries.py read path: EntityNode/EntityEdge.get_by_group_ids on driver

Patch async_write.py write path: add_episode signature fix (group_id, source, source_description, reference_time)

Migrate group-id format from colon to dash (graphiti-core validator)

Update tests to match new read/write/group-id surface

Run full unit + smoke + integration test suite (667 passing)

Re-attempt Lilymay seed; surface next blocker (LLM/embedder not wired)

Decide with user: wire Gemini+embedder OR defer Lilymay seed to Phase 2 ahead of FEAT-PH2-001
Path B has surfaced more than expected. Pausing for a decision.
What's now fixed and committed-ready (test suite: 695/696 — only the pre-existing mypy-env failure):

Read API — queries.py now uses EntityNode.get_by_group_ids / EntityEdge.get_by_group_ids via the driver, with a _read_student_partition seam that also swallows graphiti-core 0.29's GroupsNodesNotFoundError / GroupsEdgesNotFoundError (which it raises for empty partitions).
Write API — async_write.py now calls add_episode with the real graphiti-core 0.29 signature (group_id singular, source=EpisodeType.json, source_description="flush:F3:..." carrying the flush-id audit string, reference_time).
Group-id format — student:lilymay → student-lilymay etc. (graphiti-core 0.29's validator rejects colons; only [A-Za-z0-9_-]). Constants and tests migrated; module docstring updated.
What just surfaced as the next blocker:

A direct probe call (inner.add_episode(group_id='student-lilymay', ...)) fails with openai.AuthenticationError: Incorrect API key provided: not_needed. The reason: graphiti_client.py:305 constructs Graphiti(graph_driver=driver) with no llm_client, embedder, or cross_encoder — graphiti-core defaults all three to OpenAI. The GraphitiConnectionConfig.llm_provider="gemini" and embedder_url="http://promaxgb10-41b1:8001/v1" fields are config-only — never consumed during construction.

So add_episode reaches for OpenAI's responses.parse, gets the literal placeholder not_needed from OPENAI_API_KEY, and 401s. Every one of the 25 seed writes fails this way.

To unblock Gate 2 properly we'd need to:

Install whatever graphiti-core[<extra>] package gives us a Gemini LLM client + a custom-URL embedder client (probably [google-genai] or similar).
Construct those clients in get_client with the existing config fields.
Pass them into Graphiti(graph_driver=..., llm_client=..., embedder=..., cross_encoder=...).
Probably also handle the cross-encoder (graphiti-core defaults that to OpenAI too).
That's another 30–60 min of focused work, and the LLM call itself is 78s per write per the Phase-1 latency spike — so even after wiring, seeding 25 entities serially is ~30 min of LLM time. (Concurrency would be capped by the Gemini rate limit.)

This is bigger than Path B as scoped. What I've shipped already is real value — the codebase moves from "tests-only-green" to "actually compatible with graphiti-core 0.29 in three different surfaces." But the live LLM-driven extraction was never wired in Phase 1, and that's the next domino.

Recommendation
Stop the rabbit hole here. Capture this exact finding in phase-1-validation.md as a falsified Phase-1 success criterion (G2 + G3 cannot be exercised against live graphiti — the graphiti integration was tests-only-green, not runtime-green). Open a Phase-2 leading task "Graphiti runtime integration repair" (LLM+embedder+cross-encoder wiring, optional re-test) to land before FEAT-PH2-001, since gamification reads/writes depend on it.

This is exactly what the close-out gates are designed to reveal. Better to discover this now than mid-FEAT-PH2-001.

Alternative: If you'd rather press on, I can wire Gemini + the GB10 embedder now and re-attempt — but that's substantial unscoped work, plus the seed itself is a 30-min LLM-bound run. Probably better delegated to autobuild as its own task.

How do you want to proceed?

(C) Stop, write phase-1-validation.md capturing the runtime-integration falsification + create a Phase-2 leading task; defer Lilymay seed and Gate 3 demo until that task lands.
(B'') Press on now: wire Gemini LLM + GB10 embedder + cross-encoder, re-attempt seed.
Either way, the three patches already in flight (read API, write API, group-id format) are net wins regardless — they'd block whichever Phase-2 path comes next. Want me to also commit those now while you decide?

C
Update Todos

Patch queries.py read path (graphiti-core 0.29 API)

Patch async_write.py write path (graphiti-core 0.29 API)

Migrate group-id format from colon to dash

Update tests + run full suite (667 passing)

Diagnose Lilymay seed failure → LLM/embedder not wired

Write docs/research/ideas/phase-1-validation.md (held/drifted/falsified/changes)

Create Phase-2 leading task: Graphiti runtime integration repair

Summarise + offer to commit the three repair patches
Read phase-2-build-plan.md (lines 146-225)
Bash Outline phase-1-scope.md structure
IN
grep -n "^### \|^## \|Success Criteria\|Do-Not-Change\|G[0-9]\b\|G1[0-9]\b" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-1-scope.md | head -40

OUT
3:## For: Claude Code `/system-arch` → `/system-design` → `/system-plan` → `/feature-spec` → `/feature-plan` → AutoBuild
4:## Date: 17 April 2026 (last updated 23 April 2026)
5:## Status: Ready to consume — execute starting Saturday 26 April (weekend 2 of the 31-day burn)
6:## Predecessor: `phase-0-scope.md`, `phase-0-build-plan.md` (Phase 0 completes Friday 24 April), `rag-grounding-design.md`, `openwebui-rag-empirical-findings-2026-04-23.md`
7:## Successor: `phase-2-scope.md` (sketch exists; build plan written Phase 1 Thursday 30 April per hybrid cadence)
8:## Context: The load-bearing phase. Turns the Phase 0 MCP-accessible tutor into a genuinely three-layer adaptive system: fine-tuned behaviour (Layer 1, already in Phase 0) + curriculum RAG (Layer 2, now with source-typed grounding — see FEAT-PH1-004) + Graphiti student model (Layer 3, newly built) + DeepAgents tutoring loop with Player-Coach quality monitor orchestrating all three.
12:## Post-empirical update — 2026-04-23
26:## Motivation
38:## Scope: Three Features + Continuing Structural Requirements
42:### SR-08: Graphiti write-back asynchrony
52:### SR-09: Runtime LLM parameters are explicit and asserted
62:### FEAT-PH1-001: Graphiti Student Model
153:### FEAT-PH1-002: Session Planner
199:### FEAT-PH1-003: DeepAgents Tutoring Loop with Coach Quality Monitor
260:### FEAT-PH1-004: Primary-Text RAG + Source-Typed Quote Verification
331:## Do-Not-Change
351:## Success Criteria
385:## Knock-on to Phase 2
396:## Relationship to the roadmap
411:## Future fine-tune inputs (not a Phase 1 deliverable)
Bash Find success criteria and DNC items
IN
grep -n "Success criteria\|^- .*\b[Gg][0-9]\|^[0-9]*\. \|Do-Not-Change\|do not change" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-1-scope.md | head -50

OUT
170:1. If student provided a topic override, use it. Skip ranking.
171:2. Active quest or daily challenge matching an available topic (Phase 2 — not in Phase 1)
172:3. Topic with lowest TopicConfidence percentage, not revised in the last 48 hours
173:4. Topic where a recent Misconception was recorded, not yet revisited
174:5. Text or topic that unlocks a near-unlockable achievement (Phase 2 — not in Phase 1)
175:6. Random selection from `developing` confidence band
331:## Do-Not-Change
355:1. **Graphiti latency spike published.** `docs/research/ideas/graphiti-latency-spike-results.md` exists, contains real measurements from the Saturday morning spike, and informs the tool classification decisions.
357:2. **Student model populated for Lilymay.** Seeding script run; `get_student_state("lilymay")` returns a realistic baseline matching current known state (topic confidence for Macbeth, streak count, target grade).
359:3. **Session planner produces explainable plans.** `get_topic_recommendations("lilymay", count=3)` returns three topics with a brief rationale per topic (lowest confidence; recent misconception; etc.). Human review confirms the ranking matches intuition for a few test cases.
361:4. **Player-Coach tutoring loop runs end-to-end.** A full session (start → 5+ turns → end) completes with Coach evaluations recorded for each turn. At least one rejection-and-regeneration observed in testing. p95 turn latency under 30 seconds.
363:5. **Session completion writes to Graphiti.** A completed session produces a `session_completed` episode with topic coverage, AO list, turn count, and a narrative summary. Subsequent sessions for the same student benefit from the prior context.
365:6. **The demo flow works end-to-end.** From Open WebUI or Claude Desktop: start a session → have 3–5 turns with the tutor → end the session → start a new session → observe the planner recommending a different topic informed by the first session's state change.
367:7. **Six parity surfaces still green.** SR-01 through SR-07 pass their acceptance criteria against Phase 1 code.
369:8. **Technical write-up has content, not stubs.** `docs/submission/technical-writeup.md` now has real paragraphs in the three-layer architecture section, the Graphiti student model section, and the Player-Coach loop section.
371:9. **Phase 2 build plan drafted.** Thursday evening work produces `phase-2-build-plan.md` based on what Phase 1 measured and shipped. Pre-weekend-3 setup complete.
373:10. **Phase 1 validation gate run for Phase 0.** `phase-0-validation.md` produced early in Phase 1 reviewing what held, what drifted, what was falsified in the Phase 0 plan. Per the hybrid cadence approach doc.
375:11. **Source-typed corpus ingested.** `domains/gcse-english/sources/` has the four-way source-type directory structure; at least Macbeth (primary) and one study guide (secondary) populated. Ingestion produces chunk metadata with `source_type` set correctly.
377:12. **Quote verifier operational in Coach loop.** A demo session shows (a) a primary-text quote correctly attributed with act/scene, (b) a secondary-source phrase correctly rewritten as paraphrase with *"as one critic notes"*-style attribution, (c) a fabricated quote correctly stripped. Logged events visible in session summary.
379:13. **Dynamic retrieval decision observable.** At least one session where the planner targets Shakespeare triggers retrieval; at least one where the planner targets An Inspector Calls (in-copyright) skips retrieval and logs `retrieval_skipped: analysis_mode`.
381:14. **SR-09 smoke assertion passes.** `ollama show` and runner log grep both confirm `num_ctx` and `num_predict` reach the runner at Modelfile-declared values. Regression test added to CI (or manual walkthrough if CI absent in Phase 1).
Bash Read Do-Not-Change section
IN
sed -n '331,355p' /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-1-scope.md

OUT
## Do-Not-Change

These decisions are closed for Phase 1. Reopenable only per `decisions-log-2026-04-17.md §Revision policy`.

- **The six parity surfaces from LES1 remain load-bearing.** SR-01 through SR-07 apply to every Phase 1 change. New code can not regress them.
- **Graphiti topology per DEC-02** — FalkorDB on Synology, Gemini for entity extraction, GB10 for embeddings. No alternative hosting evaluated in Phase 1.
- **Graphiti write-back is always async from the caller's perspective** — SR-08. Even if the spike shows low latency.
- **Planner is deterministic, not LLM-backed.** LLM-backed planner is a Phase 2 consideration if gamification demands probabilistic variety.
- **Coach uses a different provider than Player.** Two-provider separation is an explicit invariant from agentic-dataset-factory. Both on Gemma 4 via Ollama is not acceptable even if cheaper.
- **No gamification state in Phase 1.** XP numbers from `docs/gamification/design.md` are documented but not emitted from Phase 1 code. `session_completed` episodes include turn count and topic data; Phase 2 gamification engine reads them.
- **No Reachy integration in Phase 1.** Stretch phase, separate conversation starter, 4 May gate.
- **In-memory session state only for Phase 1.** If a session_id spans an MCP server restart it's lost. Persistent session state is a Phase 2 consideration if UX requires it.
- **Single student.** Lilymay is the only student_id in Phase 1. Multi-student is post-hackathon even though the schema supports it.
- **Bedrock from Phase 0 remains the demo-week inference backup.** Phase 1 doesn't rebuild the Bedrock import; it only extends the LLM client with per-provider dispatch (which was done in Phase 0 FEAT-PO-004).
- **Retrieval is selective, not always-on.** The dynamic retrieval decision (FEAT-PH1-004 item 2) is not optional — every `tutor_turn` passes through it. Always-on retrieval is explicitly rejected based on 23 Apr empirical findings.
- **In-copyright primary texts are not in the corpus.** Analysis Mode Only per rag-grounding-design §1a. No workarounds (no DRM-ripped Kindle, no unauthorised Scribd/archive.org copies). Phase 2 per-student Text episodes are the only future legitimate path.
- **Quote verification is post-hoc, not pre-generation.** Phase B embedded-context grounding is explicitly deferred. Phase 1 ships only the post-hoc verifier (Phase A MVP shape).

---

## Success Criteria

Phase 1 is complete when all of the following are true:

1. **Graphiti latency spike published.** `docs/research/ideas/graphiti-latency-spike-results.md` exists, contains real measurements from the Saturday morning spike, and informs the tool classification decisions.
Now I have what I need. Writing phase-1-validation.md.

Write phase-1-validation.md
102 lines
# Phase 1 Validation Gate

## Date written: 2026-05-02 (Saturday — Phase 1→Phase 2 boundary, slipped one day from the planned Friday-evening seeding per the Phase-2 build plan §"Must be green by Friday 1 May evening" checklist)
## Status: **Drafted as a working seed.** Final marks against each Phase 1 success criterion (1–14) and each `phase-1-scope.md §Do-Not-Change` item are filled in below; the load-bearing finding is the **falsification of G2 + G3** (live runtime against graphiti — the integration was tests-only-green, never runtime-green) which redirects Phase 2's first day from "FEAT-PH2-001 spec + plan" to "Graphiti runtime integration repair → FEAT-PH2-001 spec + plan".
## Successor / consumer: `phase-2-build-plan.md` Day 1 entry (Saturday 2 May — section to be amended in lockstep with this doc).

---

## Held — Phase 1 commitments that shipped intact

These items match the spec and survived integration into the codebase. Cited via the commit or the merged module so future-me can audit at a glance.

- **G1 — Graphiti latency spike published.** `docs/research/ideas/graphiti-latency-spike-results.md` exists with real measurements (`add_episode` median 78.98s; `search_nodes` 0.07s, 2026-04-27). Informed `SR-08` elevation to load-bearing and `ADR-ARCH-019`'s broadening of async write-back to every flush point. Held.
- **G4 (partial) — Player-Coach tutoring loop architecture.** FEAT-PH1-003 merged at commit `bb42a28` (`feat(FEAT-PH1-003): land DeepAgents tutoring loop with Coach`). The orchestrator at [src/study_tutor/tutoring/orchestrator.py](src/study_tutor/tutoring/orchestrator.py) wires Player + Coach + QuoteVerifier behind clean Protocol seams; Coach runs on a different provider than Player; the misconfigured-loop guard rejects same-provider configurations. Architecture held; **runtime end-to-end execution unverified — see G3/G4/G6 falsifications below.**
- **G7 — Six parity surfaces SR-01..SR-07 still green.** No regression introduced by FEAT-PH1-001..004 work. Live unit + smoke + integration suite is **695/696** with the venv on PATH; the single failure (`tests/unit/planner/test_protocols.py::test_mypy_strict_accepts_structurally_conforming_rule`) is a pre-existing dev-machine env issue (mypy installed at the system Python 3.14, not in `.venv`, so its subprocess can't resolve the editable `study_tutor` install) — last touched in commit `1e37d7e` (FEAT-PH1-002) and not introduced by Phase 1 close-out work. SR-08 (async write-back) and SR-09 (runtime LLM param assertion) honoured at the architecture and design layers per ADR-ARCH-018 / ADR-ARCH-019.
- **G9 — Phase 2 build plan drafted.** `phase-2-build-plan.md` written 2026-04-30 and revised the same day for confirmed Reachy delivery (commits `ea28ee2` and `f426aa8`). Held.
- **G10 — Phase 0 validation gate run.** `phase-0-validation.md` produced early in Phase 1; cadence honoured.
- **G11 (architecturally) — Source-typed corpus ingested.** `src/study_tutor/knowledge/{corpus_models.py,corpus.py,retrieval.py}` shipped via FEAT-PH1-004 (PRV-002 / PRV-003 / PRV-004 in `tasks/completed/`). The four-way source-type structure exists in [domains/gcse-english/sources/](domains/gcse-english/sources/). Pydantic source-type discriminator is present at [src/study_tutor/knowledge/corpus_models.py](src/study_tutor/knowledge/corpus_models.py). **Live ingestion against real text payloads not exercised in Phase 1 — would surface the same LLM-wiring gap as G2 if attempted; see falsification cluster.**
- **G12 (architecturally) — Quote verifier operational in Coach loop.** Verifier integrated into orchestrator at [src/study_tutor/tutoring/orchestrator.py:460-461](src/study_tutor/tutoring/orchestrator.py#L460-L461) (`QuoteVerifierLike` Protocol; `_apply_coach_handover`). Six-criterion rubric at [src/study_tutor/tutoring/coach/rubric.py:200](src/study_tutor/tutoring/coach/rubric.py#L200) carries `quote_fidelity=0.20`. **Demo-session evidence not captured — see G3 falsification.**
- **DNC: Single student.** Lilymay is the only `student_id` referenced. Held.
- **DNC: Coach uses a different provider than Player.** Misconfigured-loop guard at orchestrator init enforces this at runtime. Held.
- **DNC: No gamification state in Phase 1.** No gamification code in `src/`. Held.
- **DNC: No Reachy integration in Phase 1.** Confirmed; Reachy delivery moved to 8 May, integration thread runs Phase 2-or-later. Held.
- **DNC: In-memory session state only.** No persistent session-state code in Phase 1. Held.
- **DNC: Retrieval is selective.** Dynamic-retrieval-decision module exists at [src/study_tutor/knowledge/retrieval.py](src/study_tutor/knowledge/retrieval.py). Held architecturally; live behavioural validation pending (G13 falsified by the same root cause as G2/G3).
- **DNC: In-copyright primary texts are not in the corpus.** No copyrighted text payloads checked into `domains/`. Held.
- **DNC: Quote verification is post-hoc, not pre-generation.** The verifier runs after Player generation in the orchestrator, before Coach handover. Held.

---

## Drifted — items that shipped but with material deviations from the Phase 1 spec

These changes are real but small enough that downstream Phase-2 plans don't need to be redrawn around them — they just need to be acknowledged so the spec and the code stop disagreeing.

- **DNC drift: Group-id format moved from colon to dash during close-out.** `phase-1-scope.md §FEAT-PH1-001` and `student_model.py` originally specified `student:<student_id>`, `subject:<subject_slug>`, `fleet:appmilla`. graphiti-core 0.29's `GroupIdValidationError` rejects characters outside `[A-Za-z0-9_-]`, so the runtime constants migrated to `student-<student_id>`, `subject-<subject_slug>`, `fleet-appmilla` during the Phase-1 close-out repair sweep (2026-05-02). Module docstring and three test files updated; cross-repo divergence note (specialist-agent uses `appmilla-fleet`) preserved. **Consequence for Phase 2:** none structurally — gamification group ids will use the dash form from day one. Update `phase-2-scope.md` if it cites the colon form anywhere.
- **G14 partial drift — SR-09 smoke assertion lives at the design layer, not as live runner output.** ADR-ARCH-018 promotes SR-09 to `CC-14` and the two-part smoke test pattern is documented; the architectural establishment is held. Live `ollama show` walkthrough against a running instance is not in the captured evidence; that's a "complete the test, don't redesign it" item rather than a structural drift.
- **Stale task-state hygiene.** `tasks/in_review/TASK-REV-AB7A-analyze-failed-autobuild-feat-70a4.md` is `status: review_complete` but still in `in_review/`. Move-to-`completed/` sweep needed. `tasks/backlog/primary-text-rag-and-quote-verifier/` still contains stub `IMPLEMENTATION-GUIDE.md` and `README.md` after the seven PRV tasks shipped; stub directory can be deleted. Cosmetic; not blocking.

---

## Falsified — Phase 1 commitments that did not actually ship at runtime

The cluster below was the load-bearing finding of the close-out gate run. Each item ships **at the architecture and unit-test layers** but **fails when exercised against a live graphiti-core 0.29 client.** The autobuild gate stayed green throughout Phase 1 because the entire graphiti integration is tested behind mocks — no test in `tests/` ever talks to a real `Graphiti` instance. The drift surfaces only at runtime, which is exactly what the close-out gates are designed to detect.

### Root cause: `src/study_tutor/knowledge/graphiti_client.py:get_client` is structurally incomplete.

`get_client(config)` constructs `Graphiti(graph_driver=driver)` with **no `llm_client`, no `embedder`, and no `cross_encoder`** — graphiti-core 0.29 then defaults all three to OpenAI clients keyed off `OPENAI_API_KEY`, which in this project is the placeholder `not_needed`. The `GraphitiConnectionConfig` fields `llm_provider="gemini"`, `llm_model="gemini-2.5-pro"`, and `embedder_url="http://promaxgb10-41b1:8001/v1"` exist but are never consumed during Graphiti construction. Result: every `add_episode` call (which graphiti-core 0.29 implements as an LLM-driven entity-extraction round-trip) hits OpenAI's `responses.parse` endpoint and 401s with `Incorrect API key provided: not_needed`.

### Falsified items

- **G2 — Student model populated for Lilymay.** `python scripts/seed_student_model.py` runs to exit code 0 but **0 of 25 entity writes persist** (all fail in `_perform_write` with `openai.AuthenticationError` once the LLM/embedder root cause is reached). The `seeded Lilymay baseline (subjects=0, confidences=0, succeeded_writes=25)` log line is misleading: `succeeded_writes` counts tasks that completed without abandonment in the drain window — it does not count tasks that actually wrote to FalkorDB. Verified empty: `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns `{"message":"No relevant nodes found","nodes":[]}` and `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])` returns `{"message":"No episodes found","episodes":[]}`. **Falsified.**
- **G3 — Session planner produces explainable plans, exercised against live state.** `get_topic_recommendations("lilymay", count=3)` reads via the same broken client path. Cannot be exercised end-to-end until G2's blocker is cleared. Pure-functional ranking module ([src/study_tutor/planner/](src/study_tutor/planner/)) is correct; it just has nothing to read. **Falsified at the runtime layer; held at the unit-test layer.**
- **G4 (runtime) — Player-Coach tutoring loop runs end-to-end.** `tutor_start_session` calls `get_student_state` which hits the same client path. The orchestrator architecture is sound (see Held above); the runtime hop into graphiti will fail with the same `AuthenticationError` until the LLM/embedder are wired. **Falsified at the runtime layer.**
- **G5 — Session completion writes to Graphiti.** F3 `record_session_completion` dispatches via `GraphitiWriteHelper.schedule_write` → `_perform_write` → `add_episode`. Same OpenAI default; same 401. **Falsified at the runtime layer.**
- **G6 — End-to-end demo flow works.** Cannot run without G2/G4/G5. **Falsified.**
- **G8 — Technical write-up has content, not stubs.** `docs/submission/technical-writeup.md` not yet drafted with real content. Not blocking but acknowledged. **Falsified for now; defer-into-Phase-2 acceptable per Phase 1 G5's allowance and per the Phase-2 build plan's "POLISH-WRITEUP" continuous track.**
- **G13 — Dynamic retrieval decision observable in a session.** Cannot be observed without a running session. **Falsified at the runtime layer; module logic correct in unit tests.**

### Secondary findings discovered during the close-out repair sweep (2026-05-02)

These were also broken and have been fixed in-flight; they would have surfaced as the next blockers behind the LLM-wiring root cause regardless. Capturing them here so the audit trail is complete.

- **Read API mismatch.** `queries.py:get_student_state` called `inner.search_nodes(group_ids, "")` and `inner.search_memory_facts(group_ids, "")` — neither exists on graphiti-core 0.29's `Graphiti` class (those are graphiti **MCP server** tool names, not library methods). **Patched 2026-05-02:** new `_read_student_partition` seam in [src/study_tutor/knowledge/queries.py](src/study_tutor/knowledge/queries.py) calls `EntityNode.get_by_group_ids(driver, group_ids, limit=...)` / `EntityEdge.get_by_group_ids(...)` and swallows graphiti-core 0.29's `GroupsNodesNotFoundError` / `GroupsEdgesNotFoundError` (raised on empty partitions, which is the bootstrap case). Legacy `search_nodes`/`search_memory_facts` duck-type still recognised by the seam for backwards-compatible test mocks. Tests green.
- **Write API mismatch.** `async_write.py:_perform_write` called `add_episode(name=..., episode_body=..., group_ids=..., flush_id=...)` — graphiti-core 0.29 takes `group_id` (singular), and has no `flush_id` parameter. **Patched 2026-05-02:** new `_add_episode_kwargs(...)` helper at [src/study_tutor/knowledge/async_write.py](src/study_tutor/knowledge/async_write.py) builds the right kwargs (`source=EpisodeType.json`, `source_description=f"flush:{flush_id}:{name}"`, `reference_time=now()`, `group_id=group_ids[0]`). The flush-id audit string still rides into structured logs unchanged; the CC-13 single-call-site invariant is preserved (greppable; AST lint still passes).
- **Group-id format mismatch.** Documented under Drifted above; tracked here too because the same close-out commit migrated the live constants.

### Why the autobuild stayed green

Three interlocking reasons. None of them are individually wrong; together they were enough to mask the runtime gap for the entire Phase 1 sprint:

1. `tests/unit/knowledge/test_queries.py:_FakeInner` and `tests/unit/knowledge/test_async_write.py:FakeClient` duck-type the *intended* graphiti API, not the real one. The mock's `search_nodes(group_ids, query)` and `add_episode(*args, **kwargs)` look right against the spec but never run against `graphiti-core 0.29`'s actual surface.
2. `tests/integration/test_rag_end_to_end.py` covers RAG/quote-verifier integration — corpus loader, retrieval, verifier, coach handover — but does **not** boot a live `Graphiti` client. RAG and verifier are graphiti-independent.
3. There is no smoke test that imports `graphiti-core` and exercises a one-shot `add_episode` against a stubbed driver. Such a test would have caught the kwargs/group-id/LLM-wiring drift before Phase 1 closed.

---

## Changes-current-phase — what this gate forces in Phase 2

This section is the consumer-facing payload for `phase-2-build-plan.md` Day 1. The gate findings change Saturday 2 May's plan in three concrete ways.

1. **New leading task before FEAT-PH2-001: "Graphiti runtime integration repair."** Spec'd as `tasks/backlog/graphiti-runtime-integration-repair/` (new). Scope: wire Gemini LLM client + GB10 embedder + cross-encoder into `get_client(config)`, install whatever `graphiti-core[<extra>]` packages are needed for the Gemini client class, add a one-shot smoke test that boots a real Graphiti instance and round-trips a single `add_episode` + `EntityNode.get_by_group_ids` against a stub or live driver, then re-run `scripts/seed_student_model.py` and verify Lilymay baseline persists. Acceptance: G2 green (live), G3/G4/G5/G6 unblocked. **Estimated complexity 6/10, ~half a day with autobuild.** Lands ahead of FEAT-PH2-001's spec + plan because gamification reads the same `get_student_state` seam that G2 needs.
2. **FEAT-PH2-001 timing slips by the integration-repair duration.** The Phase-2 build plan §"Day 1" §Morning point 3 (`/feature-spec` + `/feature-plan` for FEAT-PH2-001) waits for the new leading task. If the repair lands Saturday morning, FEAT-PH2-001 spec + plan still ship Saturday afternoon and Wave 1 still ships Saturday evening — the original Day 1 plan compresses by ~2h but stays inside Saturday. If the repair slips into Sunday, FEAT-PH2-001 Wave 1 slips one day and the Reachy/dashboard track rolls in unchanged.
3. **Three close-out-repair patches already in flight, awaiting commit.** Read-API patch ([queries.py](src/study_tutor/knowledge/queries.py)), write-API patch ([async_write.py](src/study_tutor/knowledge/async_write.py)), group-id colon→dash migration ([student_model.py](src/study_tutor/knowledge/student_model.py) + 4 test files). Tests at 695/696. These should commit ahead of the integration-repair task — both because they're on the path to G2 and because they're standalone API-correctness wins regardless of the LLM-wiring decision.

---

## Status of the close-out gate checklist (`phase-2-build-plan.md §"Must be green by Friday 1 May evening"`)

Captured here for the audit trail; this is a snapshot of where the five items landed when the gate was actually run on Saturday 2 May:

| Gate | Status | Notes |
|---|---|---|
| FEAT-PH1-004 status decided | ✅ Path A (shipped) | Verifier at orchestrator.py:460-461; six-criterion rubric live; PRV-001..007 all in `tasks/completed/`; merge commit `6eb41a7`. |
| Lilymay seeded against Synology FalkorDB | ❌ Falsified | See G2 above. Three API drifts patched in-flight; LLM-wiring root cause defers to "Graphiti runtime integration repair" task. |
| End-to-end demo session via MCP run at least once | ❌ Falsified | See G6. Same root cause as G2. |
| Six parity surfaces SR-01..SR-07 still green; SR-08 + SR-09 honoured | ✅ Green | 695/696 tests; the one failure is a pre-existing dev-env mypy-on-system-Python issue, not a regression. SR-08 / SR-09 honoured at architecture + design layers (ADR-ARCH-018 / ADR-ARCH-019). |
| `phase-1-validation.md` seeded | ✅ Done (this file) | Slipped by one day relative to the build plan but landed ahead of FEAT-PH2-001 spec work. |

---

*Doc lives at `docs/research/ideas/phase-1-validation.md`. Revisit at the close of the "Graphiti runtime integration repair" task to flip the falsified G2/G3/G4/G5/G6 entries to held — at which point Phase 1 is structurally complete on its own terms, even though the close-out exercise crossed the calendar boundary.*
Update Todos

Patch queries.py read path (graphiti-core 0.29 API)

Patch async_write.py write path (graphiti-core 0.29 API)

Migrate group-id format from colon to dash

Update tests + run full suite (667 passing)

Diagnose Lilymay seed failure → LLM/embedder not wired

Write docs/research/ideas/phase-1-validation.md (held/drifted/falsified/changes)

Create Phase-2 leading task: Graphiti runtime integration repair

Summarise + offer to commit the three repair patches
Now creating the Phase-2 leading task. Let me first check what task-file format the project uses.

Bash Inspect backlog dir + sample task structure
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/backlog/ 2>/dev/null; echo "---peek a recent backlog task---"; ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/backlog/graphiti-student-model/ 2>/dev/null | head -3

OUT
claude-desktop-review-fixes
feat-fix-ab7a
graphiti-student-model
po02-smoke-followups
primary-text-rag-and-quote-verifier
py314-langchain-pin-alignment
TASK-GSM-001-pydantic-entities-relationships.md
TASK-GSM-002-episode-types.md
TASK-GSM-006-seeding-script.md
TASK-IMP-B7E0-deepagents-adr-codebase-drift.md
TASK-PRV-001-pydantic-models-source-type-and-citation-anchor.md
---peek a recent backlog task---
IMPLEMENTATION-GUIDE.md
README.md
TASK-GSM-001-pydantic-entities-relationships.md
Read TASK-GSM-006-seeding-script.md
Write TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
89 lines
---
id: TASK-PH2-GR-001
title: Graphiti runtime integration repair — wire Gemini LLM + GB10 embedder + cross-encoder
task_type: feature
parent_validation: phase-1-validation.md
phase: 2
implementation_mode: design-first
complexity: 6
estimated_minutes: 240
status: backlog
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
dependencies: []
blocks:
- FEAT-PH2-001
tags:
- graphiti
- llm-wiring
- embedder
- phase-1-falsification-repair
- runtime-integration
- ahead-of-FEAT-PH2-001
---

# Graphiti runtime integration repair

## Why this exists

Phase 1 close-out gate (`docs/research/ideas/phase-1-validation.md`) falsified Phase 1 success criteria G2, G3, G4, G5, G6, and G13. Root cause: `src/study_tutor/knowledge/graphiti_client.py:get_client(config)` constructs `Graphiti(graph_driver=driver)` with **no `llm_client`, no `embedder`, and no `cross_encoder`**, so graphiti-core 0.29 defaults all three to OpenAI clients keyed off `OPENAI_API_KEY` (which in this project is the placeholder `not_needed`). Every `add_episode` call (which graphiti-core implements as an LLM-driven entity-extraction round-trip) 401s against OpenAI before reaching FalkorDB. The Phase 1 autobuild stayed green because every graphiti test mocks the integration; nothing in `tests/` ever booted a real `Graphiti` instance.

This task is the Phase 2 leading task — must land **before** FEAT-PH2-001 spec + plan because gamification reads `get_student_state` and writes `GamificationState` through the same broken client path.

## Acceptance criteria

1. **AC-001 — Gemini LLM client wired.** `get_client(config)` constructs a Gemini-backed `LLMClient` keyed off `GOOGLE_API_KEY` and `config.llm_model` (default `"gemini-2.5-pro"`) and passes it to `Graphiti(...)`. Whatever `graphiti-core[<extra>]` install gives us the Gemini client class is added to the Phase 1 setup checklist in `phase-1-build-plan.md` (and to a new `[knowledge-graph]` extra in `pyproject.toml` so future `uv pip install` / `pip install -e .[knowledge-graph]` runs are reproducible).
2. **AC-002 — Custom-URL embedder wired.** `get_client` constructs an embedder pointing at `config.embedder_url` (default `"http://promaxgb10-41b1:8001/v1"` — the GB10 vLLM service) and passes it to `Graphiti(...)`. If the embedder client class needs an extra, it's bundled into the same `[knowledge-graph]` extra as AC-001.
3. **AC-003 — Cross-encoder wired (or explicitly disabled).** Decide between (a) wiring a Gemini-backed cross-encoder, (b) wiring a no-op stub that bypasses reranking, or (c) leaving the OpenAI default and documenting that retrieval reranking is degraded. Ship one of these and document the choice inline. The decision must not silently cost OpenAI tokens at runtime — that's the failure mode we just dug ourselves out of.
4. **AC-004 — Smoke test exercising live graphiti-core.** New `tests/smoke/test_graphiti_live_smoke.py` (or equivalent location) that boots a `Graphiti` instance against a stubbed driver and exercises one round-trip: `add_episode(...)` → `EntityNode.get_by_group_ids(...)` → assertion that the episode is reachable. The test must fail loudly if `LLMClient`/`Embedder`/`CrossEncoder` defaults regress to OpenAI in future. The CC-13 regex audit (single `add_episode(` call site in `src/`) continues to pass.
5. **AC-005 — `python scripts/seed_student_model.py` lands Lilymay's baseline against the live Synology FalkorDB.** All 25 entity writes succeed. `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns the Student entity with the expected attributes. `get_student_state(client, "lilymay")` returns a non-empty `StudentState` (year_group=11, target_grade="8", non-empty subjects, non-empty topic_confidences). Re-running the seed is idempotent (`event=seeding_skipped`).
6. **AC-006 — End-to-end demo session via MCP runs at least once.** `tutor_start_session` → 5–7× `tutor_turn` → `tutor_session_end` from Claude Desktop, with at least one Coach revision observed and a `session_completed` episode written to Graphiti and visible via `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])`. This unblocks Phase 1 G3 + G4 + G5 + G6 + G13. Capture turn p50/p95 latency in `phase-1-validation.md` (revisit trigger flagged in `phase-2-build-plan.md §"What is TBD"`).
7. **AC-007 — `phase-1-validation.md` updated.** The five falsified items (G2, G3, G4, G5, G6, G13) flip from "Falsified" to "Held" with the live evidence inline. Phase 1 is then structurally complete on its own terms.

## Out of scope

- **Coach calibration pass** (separate Phase 2 nice-to-have per `phase-2-build-plan.md §"Should be green; can absorb on Saturday morning"`). The repair task only needs the runtime to work; it doesn't need the Coach to be optimally tuned.
- **Multi-student support.** Single-student (Lilymay) is the Phase 1+2 invariant.
- **Index migration.** If FalkorDB has stale indices from earlier seed attempts that produce `Connection closed by server` warnings during `build_indices_and_constraints`, those warnings are background-task noise that don't block the main flow. Investigate only if the warnings escalate into actual write failures after the LLM/embedder fixes land.
- **Adding gamification fields to `tutor_session_end`** — that's FEAT-PH2-001 item 4 and stays in FEAT-PH2-001's own subtask list.

## Already-fixed-in-flight (commit before starting this task)

These three patches landed during the close-out gate run on 2026-05-02 and are awaiting commit. They're prerequisites for this task — both because they're on the same call path and because they're standalone API-correctness wins regardless of the LLM-wiring outcome.

- **Read API**: `queries.py:_read_student_partition` seam now calls `EntityNode.get_by_group_ids` / `EntityEdge.get_by_group_ids` on the driver, with a duck-typed shortcut for legacy `search_nodes`/`search_memory_facts` test mocks. `GroupsNodesNotFoundError` / `GroupsEdgesNotFoundError` swallowed (bootstrap case).
- **Write API**: `async_write.py:_add_episode_kwargs` builds graphiti-core 0.29's real signature: `source=EpisodeType.json`, `source_description=f"flush:{flush_id}:{name}"`, `reference_time=now()`, `group_id=group_ids[0]` (singular). Flush-id audit string still rides into structured logs unchanged.
- **Group-id format**: `student:` → `student-`, `subject:` → `subject-`, `fleet:appmilla` → `fleet-appmilla` (graphiti-core 0.29's `GroupIdValidationError` rejects characters outside `[A-Za-z0-9_-]`). Constants in `student_model.py` updated; module docstring updated; cross-repo divergence note preserved; tests updated in `test_student_model.py`, `test_graphiti_client.py`, `test_session_end.py`, `test_async_write.py`.

Tests at 695/696 (the one failure is a pre-existing dev-machine `mypy`-on-system-Python env issue from FEAT-PH1-002, not introduced by this work).

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gemini rate limits hit during 25-entity seed | Medium | Medium | Seed serially with a small inter-write delay; the script already drains via `helper.drain()` so a slow path is acceptable. Per the 2026-04-27 latency spike, `add_episode` median is 78s — 25 sequential writes is ~30 min. Acceptable for a one-off seed. |
| Embedder URL unreachable at smoke-test time | Medium | Low | The smoke test (AC-004) uses a stubbed driver, not the live FalkorDB; embedder reachability only matters at AC-005 / AC-006 time. If GB10 is down, defer AC-005/006 by the GB10 outage duration; fall back to a local embedder for the demo if outage persists past Saturday afternoon. |
| Cross-encoder choice (AC-003) blocks on a graphiti-core API decision | Low | Low | Default to (b) — a no-op cross-encoder stub — if the wired option doesn't surface cleanly. Reranking quality is not load-bearing for the Phase 2 demo. |
| Stale indices on FalkorDB from earlier broken seed attempts | Medium | Low | The `Connection closed by server` warning during `build_indices_and_constraints` looked like a transient FalkorDB-side issue, not a hard blocker. If it returns post-fix, drop the `study_tutor` database and re-create. |

## Implementation hint (non-binding — re-derive during `/feature-plan`)

Likely subtask shape (3–4 waves, ~5 subtasks):

- **Wave 1 — `pyproject.toml` `[knowledge-graph]` extra + setup-checklist update.** Declare the Gemini + embedder extras. ~15 min.
- **Wave 2 — `get_client` LLM/embedder/cross-encoder construction.** New helper functions + integration into `get_client`. ~60 min.
- **Wave 3 — Live smoke test + CC-13 regex audit verification.** ~45 min.
- **Wave 4 — Re-run seed, capture verification evidence (`mcp__graphiti__search_nodes` output), update `phase-1-validation.md`.** ~30 min plus the seed's own ~30 min LLM-bound runtime.
- **Wave 5 — End-to-end demo session via MCP, capture turn p50/p95.** ~30–45 min.

Total: ~half a day (4 hours) plus the seed's LLM-bound runtime.

## Cross-references

- `docs/research/ideas/phase-1-validation.md` — the gate that falsified G2/G3/G4/G5/G6/G13 and triggered this task.
- `docs/research/ideas/phase-1-scope.md §FEAT-PH1-001` "Group IDs" — original colon-form spec; superseded by the dash-form note in `student_model.py`.
- `docs/research/ideas/phase-2-build-plan.md §"Day 1"` — must be amended to insert this task between the validation gate and FEAT-PH2-001 spec + plan.
- `docs/research/ideas/graphiti-latency-spike-results.md` — `add_episode` median 78s; informs the seed-runtime estimate.
- `tests/unit/knowledge/test_queries.py:_FakeInner` and `tests/unit/knowledge/test_async_write.py:FakeClient` — the mocks that let the integration drift through Phase 1; AC-004's smoke test is the regression-prevention complement.
Update Todos

Patch queries.py read path (graphiti-core 0.29 API)

Patch async_write.py write path (graphiti-core 0.29 API)

Migrate group-id format from colon to dash

Update tests + run full suite (695/696)

Diagnose Lilymay seed failure → LLM/embedder not wired

Write docs/research/ideas/phase-1-validation.md

Create Phase-2 leading task: TASK-PH2-GR-001 graphiti runtime integration repair

Summarise + offer to commit the three repair patches
Done — Phase 1 close-out captured.
Two new docs
docs/research/ideas/phase-1-validation.md — the four-paragraph gate: Held / Drifted / Falsified / Changes-current-phase. The load-bearing finding is the falsification cluster (G2 + G3 + G4 + G5 + G6 + G13) all rooted in one cause: get_client constructs Graphiti(graph_driver=driver) with no llm_client/embedder/cross_encoder, so graphiti-core defaults to OpenAI and 401s. The autobuild stayed green because every graphiti test mocks the integration. The doc names this explicitly so the audit trail captures why Phase 1 looked green to autobuild but couldn't be exercised live.
tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md — Phase-2 leading task. Critical priority, 7 ACs, blocks FEAT-PH2-001. Covers wiring Gemini LLM + GB10 embedder + cross-encoder, adding a [knowledge-graph] pyproject extra, a live-graphiti smoke test (the one that would have caught all this in Phase 1), re-running the seed, running the end-to-end MCP demo, and flipping the validation-doc entries from Falsified → Held. ~half a day plus the seed's ~30-min LLM-bound runtime.
Three patches in flight, awaiting commit
These are net wins regardless of when TASK-PH2-GR-001 lands — they're API-correctness fixes for graphiti-core 0.29:

Read API: queries.py — _read_student_partition seam using EntityNode/EntityEdge.get_by_group_ids + empty-partition error swallow.
Write API: async_write.py — _add_episode_kwargs building the real graphiti-core 0.29 signature.
Group-id format: student_model.py constants migrated colon → dash; 4 test files updated.
Tests: 695/696 (one failure is the pre-existing dev-machine mypy-env issue from FEAT-PH1-002, not a regression).

Phase-2 build plan needs a tiny amendment
phase-2-build-plan.md §"Day 1" Saturday morning currently goes:


1. Run Phase 1 validation gate (~30 min)
2. Update architecture and design for Phase 2 scope (~1h)
3. Spec + plan FEAT-PH2-001 (~1.5h)
Step 3 should now read:


3a. Spec + plan TASK-PH2-GR-001 (Graphiti runtime integration repair) (~30 min)
3b. Run TASK-PH2-GR-001 (~half day plus seed runtime — may slip into Sunday)
3c. Spec + plan FEAT-PH2-001, only after TASK-PH2-GR-001 lands AC-005 + AC-006
Want me to make that edit too while we're here?

Suggested commit shape
I'd recommend two commits:

fix(FEAT-PH1-004): align graphiti integration with graphiti-core 0.29 — the three API patches + the four updated test files. Mentions that the autobuild gate was tests-only-green and that this surfaces during the Phase 1 close-out exercise.
docs(phase-1): seed phase-1-validation.md and lead Phase 2 with TASK-PH2-GR-001 — the new validation doc + the new task file.
Shall I commit these now? (No push; local commits only — your call when to push to origin.)

yes
Bash Check working tree status
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor status

OUT
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   scripts/seed_student_model.py
	modified:   src/study_tutor/knowledge/async_write.py
	modified:   src/study_tutor/knowledge/queries.py
	modified:   src/study_tutor/knowledge/student_model.py
	modified:   tests/unit/knowledge/test_async_write.py
	modified:   tests/unit/knowledge/test_graphiti_client.py
	modified:   tests/unit/knowledge/test_student_model.py
	modified:   tests/unit/tutoring/test_session_end.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	docs/research/ideas/phase-1-validation.md
	tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md

no changes added to commit (use "git add" and/or "git commit -a")
Bash Diff stat summary
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor diff --stat

OUT
 scripts/seed_student_model.py                |   2 +-
 src/study_tutor/knowledge/async_write.py     |  45 ++++++++++-
 src/study_tutor/knowledge/queries.py         | 107 ++++++++++++++++++++++++---
 src/study_tutor/knowledge/student_model.py   |  46 +++++++-----
 tests/unit/knowledge/test_async_write.py     |  13 +++-
 tests/unit/knowledge/test_graphiti_client.py |   8 +-
 tests/unit/knowledge/test_student_model.py   |  18 +++--
 tests/unit/tutoring/test_session_end.py      |   8 +-
 8 files changed, 199 insertions(+), 48 deletions(-)
Bash Recent commit style
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor log --oneline -5

OUT
ff51ac8 Merge remote-tracking branch 'origin/main'
855b71a Reviews, history completed tasks
0f70046 chore: gitignore .guardkit/graphiti-query-log.jsonl (local-only diagnostics)
6eb41a7 chore(FEAT-70A4): finalize merge — archive, move tasks, clean autobuild state
4efd10d updated history
Bash Commit graphiti API alignment patches
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor add \
  src/study_tutor/knowledge/queries.py \
  src/study_tutor/knowledge/async_write.py \
  src/study_tutor/knowledge/student_model.py \
  tests/unit/knowledge/test_async_write.py \
  tests/unit/knowledge/test_graphiti_client.py \
  tests/unit/knowledge/test_student_model.py \
  tests/unit/tutoring/test_session_end.py \
  scripts/seed_student_model.py && git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor commit -m "$(cat <<'EOF'
fix(graphiti): align integration with graphiti-core 0.29 surface

Phase 1 close-out gate run on Sat 2 May surfaced three independent
API drifts in the Phase-1 graphiti integration. The autobuild gate
stayed green throughout Phase 1 because every graphiti test mocks
the integration; the drifts only show up at runtime.

- Read API: queries.py called inner.search_nodes / search_memory_facts
  (graphiti MCP tool names, not graphiti-core methods). Replaced with
  a _read_student_partition seam using EntityNode/EntityEdge.get_by_group_ids
  on the driver, swallowing GroupsNodesNotFoundError /
  GroupsEdgesNotFoundError for the empty-partition bootstrap case. Legacy
  duck-typed test mocks still recognised so existing fixtures don't break.

- Write API: async_write.py called add_episode(group_ids=, flush_id=);
  graphiti-core 0.29 takes group_id (singular) and has no flush_id slot.
  New _add_episode_kwargs helper builds the real signature
  (source=EpisodeType.json, source_description=f"flush:{flush_id}:{name}",
  reference_time, group_id=group_ids[0]). Flush-id audit string still
  rides into structured logs unchanged; CC-13 single-call-site invariant
  preserved.

- Group-id format: graphiti-core 0.29's GroupIdValidationError rejects
  characters outside [A-Za-z0-9_-]. Migrated student_model.py constants
  from colon to dash form: student- / subject- / fleet-appmilla. Module
  docstring updated; cross-repo divergence note (specialist-agent uses
  appmilla-fleet) preserved. Tests in test_student_model.py,
  test_graphiti_client.py, test_session_end.py, test_async_write.py
  updated to match. Seed-script docstring example updated.

These three patches do not unblock Gate 2 on their own — the live seed
still 401s against OpenAI because get_client() never wires the LLM,
embedder, or cross-encoder (all default to OpenAI). That remaining
gap is captured in TASK-PH2-GR-001 (separate commit). The patches are
landed now because they're API-correctness wins regardless of when the
LLM-wiring repair task runs, and they're prerequisites for it.

Tests: 695/696 (the one failure is the pre-existing dev-machine
mypy-on-system-Python env issue from FEAT-PH1-002, not introduced
here).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

OUT
[main a210472] fix(graphiti): align integration with graphiti-core 0.29 surface
 8 files changed, 199 insertions(+), 48 deletions(-)
Bash Commit validation doc + leading task; verify clean
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor add \
  docs/research/ideas/phase-1-validation.md \
  tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md && git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor commit -m "$(cat <<'EOF'
docs(phase-1): seed phase-1-validation.md; lead Phase 2 with TASK-PH2-GR-001

Captures the Phase 1 close-out gate run from Sat 2 May. The four
sections (held / drifted / falsified / changes-current-phase) name
the load-bearing finding: a falsification cluster (G2 + G3 + G4 + G5
+ G6 + G13) all rooted in get_client() not wiring an LLM client,
embedder, or cross-encoder — graphiti-core defaults to OpenAI and
401s with the placeholder OPENAI_API_KEY=not_needed. The autobuild
gate stayed green because every graphiti test mocks the integration;
no test ever booted a real Graphiti instance. This is exactly the
runtime-vs-design drift that the close-out gates are designed to
detect.

Phase-2 leading task TASK-PH2-GR-001 created at backlog. Critical
priority, blocks FEAT-PH2-001. Seven ACs cover Gemini LLM client +
GB10 embedder wiring + cross-encoder decision + a live-graphiti
smoke test (the test that would have caught all this in Phase 1) +
re-running the seed + running the end-to-end MCP demo + flipping
the validation-doc falsified entries to held. ~half a day plus the
seed's ~30-min LLM-bound runtime.

The three already-shipped API-alignment patches (previous commit)
are listed in the task's "Already-fixed-in-flight" section so the
audit trail across the two commits stays intact.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)" && git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor status

OUT
[main 78d3498] docs(phase-1): seed phase-1-validation.md; lead Phase 2 with TASK-PH2-GR-001
 2 files changed, 189 insertions(+)
 create mode 100644 docs/research/ideas/phase-1-validation.md
 create mode 100644 tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
On branch main
Your branch is ahead of 'origin/main' by 2 commits.
  (use "git push" to publish your local commits)

nothing to commit, working tree clean
Update Todos

Patch queries.py read path (graphiti-core 0.29 API)

Patch async_write.py write path (graphiti-core 0.29 API)

Migrate group-id format from colon to dash

Update tests + run full suite (695/696)

Diagnose Lilymay seed failure → LLM/embedder not wired

Write docs/research/ideas/phase-1-validation.md

Create Phase-2 leading task: TASK-PH2-GR-001 graphiti runtime integration repair

Commit graphiti API alignment + docs/task
Both commits landed locally on main, working tree clean, 2 commits ahead of origin/main:

a210472 fix(graphiti): align integration with graphiti-core 0.29 surface — 8 files, +199/−48
78d3498 docs(phase-1): seed phase-1-validation.md; lead Phase 2 with TASK-PH2-GR-001 — 2 new files, +189
Push to origin when you're ready (git push).

Where you stand for Saturday's actual VALIDATION-gate work
Phase 1 close-out is now captured. The Saturday morning slot in phase-2-build-plan.md called for:

Run Phase 1 validation gate (~30 min) — done, docs/research/ideas/phase-1-validation.md.
Update architecture and design for Phase 2 scope (/system-arch + /system-design + /system-plan) — next, ~1h.
Spec + plan FEAT-PH2-001 — needs amending to insert TASK-PH2-GR-001 before FEAT-PH2-001 (I sketched the amended sequence in the previous turn; want me to edit phase-2-build-plan.md Day 1 to reflect it?).
After step 2 (or in parallel with it), the call is whether to go straight at TASK-PH2-GR-001 yourself this morning or feed it to autobuild via /feature-spec + /feature-plan + /feature-build. Given complexity 6 and the Gemini/embedder wiring's narrow surface, I'd lean autobuild — let it churn through Waves 1–3 while you do step 2.

Want me to: (a) amend the build plan Day 1 entry to insert TASK-PH2-GR-001, (b) kick off /system-arch + /system-design + /system-plan for Phase 2 scope, or (c) something else?

please also make the edits you suggested
Read phase-2-build-plan.md (lines 215-249)
Read phase-2-build-plan.md (lines 95-124)
Now I'll edit the close-out checklist (reflect the actual gate run), the FEAT-PH1-004 branching (resolved to Path A), the Feature Summary table, and the Saturday Day-1 plan.

Edit phase-2-build-plan.md
Added 2 lines
Edit phase-2-build-plan.md
Added 2 lines
Now amend the Feature Summary table and the dependency chain to insert TASK-PH2-GR-001.

Edit phase-2-build-plan.md
Added 1 line
Read phase-2-build-plan.md (lines 124-153)
Edit phase-2-build-plan.md
Added 4 lines
Now amend the Saturday morning step sequence and the end-of-day expected state.

Edit phase-2-build-plan.md
Added 2 lines
Read phase-2-build-plan.md (lines 176-215)
Edit phase-2-build-plan.md
Added 17 lines
Now renumber the downstream steps (4 → 5, 5 → 6, etc.) since I just inserted a new step 3.

Read phase-2-build-plan.md (lines 233-267)
Edit phase-2-build-plan.md
Added 1 line
Let me also check the file's "Status" preamble and the daily roll-up table for consistency.

Read phase-2-build-plan.md (lines 741-775)
Edit phase-2-build-plan.md
Added 1 line
Edit phase-2-build-plan.md
Modified
Now let me also update the file's Status preamble to reflect the gate run results and current state.

Read phase-2-build-plan.md (lines 2-16)
Edit phase-2-build-plan.md
Modified
Verifying the file is still coherent and committing.

Bash Diff stat of build-plan edits
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor diff --stat docs/research/ideas/phase-2-build-plan.md

OUT
 docs/research/ideas/phase-2-build-plan.md | 88 +++++++++++++++++++++----------
 1 file changed, 59 insertions(+), 29 deletions(-)
Bash Verify TASK-PH2-GR-001 references inserted
IN
grep -n "TASK-PH2-GR-001" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-2-build-plan.md | head

OUT
6:## Status: **In flight as of 2026-05-02 (Saturday 2 May AM — Phase 2 Day 1).** Phase 1 close-out gate run; FEAT-PH1-001 + FEAT-PH1-002 + FEAT-PH1-003 merged; FEAT-PH1-004 (Primary-Text RAG + Quote Verifier) shipped as `FEAT-70A4` (Path A confirmed; merge commit `6eb41a7`); 6-criterion Coach with `quote_fidelity=0.20` live. The validation gate (`phase-1-validation.md`) **falsified Phase 1 G2 + G3 + G4 + G5 + G6 + G13** — root cause: `get_client()` does not wire an LLM client / embedder / cross-encoder into `Graphiti(...)`, so graphiti-core defaults to OpenAI and 401s. Three associated API drifts (read API, write API, group-id colon→dash) patched in-flight (commit `a210472`). The remaining LLM-wiring gap defers to **`TASK-PH2-GR-001` (Graphiti runtime integration repair)** — the Phase-2 leading task, must land before FEAT-PH2-001 spec + plan. **Reachy Mini "Scholar" delivery confirmed for Friday 8 May 2026** (Pollen Robotics dispatch text, received 30 April PM); DEC-06 go/no-go gate at Saturday 9 May; live Reachy demo segment is the likely outcome (capture target Wednesday 13 May). TBD items remaining: Coach calibration data, real turn p50/p95 (capturable once `TASK-PH2-GR-001` AC-006 lands), Reachy operational status post-unbox.
52:- [ ] **Lilymay seeded against Synology FalkorDB** — ❌ **Falsified.** Three API drifts surfaced and were patched in-flight (read API, write API, group-id format colon→dash) but the underlying root cause — `get_client()` not wiring an LLM client / embedder / cross-encoder, so graphiti-core defaults to OpenAI and 401s with the placeholder `OPENAI_API_KEY=not_needed` — defers to **`TASK-PH2-GR-001` Graphiti runtime integration repair** (new Phase-2 leading task; see Day 1 morning step 3 below).
53:- [ ] **End-to-end demo session via MCP run at least once** (Phase 1 G3) — ❌ **Falsified.** Same root cause as Gate 2; `tutor_start_session` calls `get_student_state` through the same broken client path. Unblocked by `TASK-PH2-GR-001`.
115:| TASK-PH2-GR-001 | Graphiti runtime integration repair (Gemini LLM + GB10 embedder + cross-encoder wiring; live-graphiti smoke test; re-run seed; run end-to-end MCP demo) | Phase 1 validation gate | 6/10 | Sat 2 May AM/PM (may slip to Sun 3 May) | ⏳ Backlog — leading task ahead of FEAT-PH2-001 |
116:| FEAT-PH2-001 | Gamification state engine + session-lifecycle integration | TASK-PH2-GR-001 (live get_student_state + add_episode), FEAT-PH1-001 (schema), FEAT-PH1-003 (session-end pipeline), FEAT-PH1-004 (Path A — 6-criterion Coach live) | 6/10 | Sat 2 – Mon 4 May (Wave 1 may slip to Sun 3 May depending on TASK-PH2-GR-001 finish) | ⏳ Scope only; spec + plan + build during Phase 2 |
129:                                              TASK-PH2-GR-001 (Sat AM/PM, may slip Sun)
158:### Saturday 2 May (Phase 2 Day 1, full day, ~6h) — Validation gate + TASK-PH2-GR-001 + FEAT-PH2-001 spec & plan + capture working-today
162:**Plan amendment after the Sat-2-May validation gate run:** the gate falsified Phase 1 G2/G3/G4/G5/G6/G13 (LLM/embedder not wired into `get_client()`; details in `phase-1-validation.md`). The repair lands as `TASK-PH2-GR-001` ahead of FEAT-PH2-001 spec/plan. If the repair finishes Saturday afternoon, FEAT-PH2-001 spec/plan + Wave 1 still ship Saturday — the day compresses by ~2h but stays inside Saturday. If the repair slips into Sunday, FEAT-PH2-001 Wave 1 slips one day and the rest of Phase 2 rolls in unchanged (the freed Sunday Reachy slot — see Sunday 3 May entry — absorbs the slip).
164:#### Morning (~3h) — Phase-1 validation gate + Phase 2 system-level re-grounding + TASK-PH2-GR-001 spec & plan
197:3. **Spec + plan + build TASK-PH2-GR-001 (Graphiti runtime integration repair)** (~30 min spec/plan + ~half day build, may run partly in background; LLM-bound seed adds ~30 min):
Edits look right. Committing.

Bash Commit phase-2 build plan amendments
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor/ add docs/research/ideas/phase-2-build-plan.md && git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor/ commit -m "$(cat <<'EOF'
docs(phase-2): amend Day 1 plan to lead with TASK-PH2-GR-001

Reflects the Sat-2-May validation gate run results into the Phase 2
build plan so the day-by-day stays load-bearing instead of stale.

- Status preamble: rewritten as "in flight Sat 2 May AM" — names
  Path A (FEAT-PH1-004 shipped), the falsification cluster
  (G2/G3/G4/G5/G6/G13), the LLM-wiring root cause, the three already-
  patched API drifts (commit a210472), and the deferral to
  TASK-PH2-GR-001.

- "Must be green by Friday 1 May evening" checklist: each item now
  carries the actual gate-run outcome (✅ FEAT-PH1-004 / ✅ SR-01..09 /
  ✅ phase-1-validation.md / ❌ Lilymay seed / ❌ end-to-end demo)
  with the falsified items pointing at TASK-PH2-GR-001 for the repair.

- "Branching for FEAT-PH1-004 outcome" section: collapsed Path A as
  the resolved outcome; Path B preserved in a <details> block for
  audit-trail only.

- Feature Summary table: VALIDATION marked ✅ done; new
  TASK-PH2-GR-001 row inserted between VALIDATION and FEAT-PH2-001;
  FEAT-PH2-001's "depends on" row updated to name TASK-PH2-GR-001.

- Dependency chain ASCII: TASK-PH2-GR-001 inserted between VALIDATION
  and FEAT-PH2-001.

- Saturday 2 May Day-1 plan: morning step 1 marked DONE; new step 3
  spec/plan/build for TASK-PH2-GR-001 inserted before the FEAT-PH2-001
  spec/plan; downstream steps renumbered (4→5, 5→6, etc.); afternoon
  Wave 1 gated on TASK-PH2-GR-001 ACs 1+2 landing first; end-of-Saturday
  state list updated to reflect the new sequence and the slip-to-Sunday
  contingency.

- TBD-markers consolidated table: FEAT-PH1-004 marked Resolved (Path A);
  new "Graphiti runtime integration" row added pointing at TASK-PH2-GR-001;
  real-turn-p50/p95 row's revisit trigger updated to depend on
  TASK-PH2-GR-001 AC-006 (end-to-end MCP demo).

- Schedule-summary row for Sat 2 May: rewritten to name
  TASK-PH2-GR-001 in the day's primary work and call out the
  slip-to-Sunday contingency.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

OUT
[main 732672c] docs(phase-2): amend Day 1 plan to lead with TASK-PH2-GR-001
 1 file changed, 59 insertions(+), 29 deletions(-)
Update Todos

Patch queries.py + async_write.py + group-id format (graphiti-core 0.29 alignment)

Update tests + run full suite (695/696)

Diagnose Lilymay seed failure → LLM/embedder not wired

Write docs/research/ideas/phase-1-validation.md

Create Phase-2 leading task: TASK-PH2-GR-001

Commit graphiti API alignment + docs/task

Amend phase-2-build-plan.md to insert TASK-PH2-GR-001 and reflect gate-run outcomes

Commit phase-2-build-plan.md amendments
Three commits now sit on local main ahead of origin/main:

a210472 fix(graphiti): align integration with graphiti-core 0.29 surface
78d3498 docs(phase-1): seed phase-1-validation.md; lead Phase 2 with TASK-PH2-GR-001
732672c docs(phase-2): amend Day 1 plan to lead with TASK-PH2-GR-001
The build plan now reflects the gate-run reality — status preamble, close-out checklist, Path-A resolution, Feature Summary, dependency chain, Saturday Day-1 sequence, end-of-day state, TBD-markers table, and schedule-summary row are all consistent.

Next move (your call)
The Phase 2 Day 1 morning sequence is now:

Validation gate ✅
/system-arch + /system-design + /system-plan for Phase 2 scope (~1h)
/feature-spec + /feature-plan for TASK-PH2-GR-001 (~30 min) → /feature-build (~half day plus ~30 min LLM-bound seed runtime)
/feature-spec + /feature-plan for FEAT-PH2-001 — gated on (3) finishing
Wave 1 of FEAT-PH2-001 + capture working-today
Want me to kick off (2) or (3) next? They can also run in parallel — (2) is doc work that doesn't depend on the runtime being live, and (3) is the runtime repair that doesn't touch architecture docs.

I think we need to close out the issues originally marked as must complete for Phase 1 close-out. please update tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md as we are NOT to use any cloud AI API's due to cost, all LLM's are served locally onthe GB10 via the TailScale network using lama-swap see /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark. Please investigate the usage of Graphiti in the guardkit repo - this has all been solved in there I'm sure and maybe we can create some tasks to pull out the Graphiti clients etc into a core library for use across repos - the study-tutor, guardkit and specialist-agent will alll use Graphiti heavily and then update the task accordingly
Show less
Let me investigate the GuardKit repo's Graphiti work and the dgx-spark / lama-swap setup before updating the task.

Bash List dgx-spark research dir
IN
ls /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark/ 2>/dev/null | head -40

OUT
dark-factory-dataset-factory-conversation-starter.md
dark-factory-economics-and-model-serving.md
DGX Spark, Nemotron3, and NVFP4: Getting to 65+ tps | by Thomas P. Braun | Avarok.pdf
gb10-model-requirements-matrix.md
llama-swap-config.yaml
llama-swap-setup.md
llama-swap-systemd-supervision.md
POST-VALIDATION-model-strategy-revision.md
qwen3.6-27b-gb10-community-research.md
README.md
RESULTS-qwen3.6-27b-validation.md
RESULTS-v2-all-llamacpp-validation.md
RESULTS-v3-production-deployment.md
RUNBOOK-qwen3.6-27b-validation.md
RUNBOOK-v2-all-llamacpp-architecture.md
RUNBOOK-v3-production-deployment.md
TASK-graphiti-yaml-endpoint-migration.md
VALIDATION-D6F4-gap-fix-results.md
VALIDATION-OPS-7CB1-9F2A-results.md
Bash List sibling repos
IN
ls /Users/richardwoollcott/Projects/appmilla_github/ 2>/dev/null

OUT
agent-os
agentecflow_platform
agentic-dataset-factory
ai-engineer
amity-client-test
amity-kotlin-openapi-generator
AndroidForAI
andy
appmilla-test-explore
architecture_books
AspNetCoreWebApiFundamentals
BarcodeScanning.Native.Maui
basic_keycloak
CertifyDatabase
CertifyMobileApplications
Circuit-Compose-App
cite-saul-ollama-setup
ClearAccept.Android
ClearAccept.TerminalApi.Protobuff
CMPNavigationDemo
ComposablePresenterCounter
ComposablePresenterCounter_template_expanded
ComposeMultiplatformDemo
composeWebApp
cryptopofthepops
CSharp_Markup_PeopleInSpace_MAUI
decompose_starter_template
DeCUK.Mobile.MyDrive
deepagents
deepagents-orchestrator-exemplar
deepagents-player-coach-exemplar
deepagents-player-coach-exemplar-original
dev-tasker
devtasker-temp
DLR.Certify.API.Legacy
DLR.Certify.API.Manufacturing
DLR.Certify.API.Onboarding
DLR.Certify.API.ProductionLineActivation
DLR.Certify.DevelopmentCertificates
DLR.Certify.Gateway
DLR.Certify.KeyCloak
DLR.Certify.Logging
DLR.Certify.Onboarding
DLR.Certify.ProductionLineActivation.Core
DLR.Certify.Proxy
DLR.Certify.ServiceHub
docling-dgx-spark-scripts
dotnet-functional-fastendpoints-exemplar
DriverScanning
engagement-assistant
EvCharging
Example-iOS-Swift
FigmaExporter
FindAndExplore
FindAndExploreApi
FindAndExploreApi copy
finproxy-docs
forge
framework_app
framework_app.iml
full_multiplatform
Functional_PeopleInSpace_MAUI
GetStarted
graphiti
guardkit
guardkit-examples
guardkit-examples copy
hack_night_images
HelloKMPTemplate
home_network
iOSAvatarViewer
iOSAvatarViewer.zip
jarvis
JetpackViewModel-CMP
JetpackViewModel-Native
jvm-js-fullstack
kiro-common-files
kiro-for-cc
kiro-steering-files
kirosteeringfiles
KMPJetpackDemo
KMPNavigationDemo
KMPNavigationEvo
KMPNavigationEvo_delete_me
kotlinwasm
ktor-api-json-placeholder
ktor-avatar-convertor
ktor-placeholder-demo
ktor-sample
lpa-platform
lpa-project-docs
MauiReactor_People_InSpace_Maui
mcp-cerebra-legal-server
mcp-code-checker
MetaKeep
MetaKeepCodeSamples
MultiplatformWithTests
music-merch-app
music-merch-app_fucked
mydrive
n8n-mcp
n8n-workflows
nats-asyncio-service-exemplar
nats-asyncio-service-exemplar-claude-desktop
nats-core
nats-infrastructure
nav_back_and_forth_crash.rtf
openformat-testapp
OpenFormatComposeMultiplatform
PeopleInSpace_MAUI
PeopleInSpace_Uno
pla-react-test
pla-react-test-original
pla-test-project
PLAReact
probate-agent
ReadyPlayerMe
RefactAITest
require-kit
rnd-retail-multiplatform-public
safe-endpoints
saul-lm-notebook
ScannerTestApp
SemanticKernel
software_factories_talk
specialist-agent
StarterApp
study-tutor
SwiftGLTF
taskwright
temp
temp_claude
terminalapi
test-fastapi-template
TipsyArtist
trading_snippet
trading_snippet.zip
tutor_agent
twitter_assistant
uk-legislation-llm
uk-legislation-notebook
uk-probate-agent
VesselSocial
vllm-profiling
vsl-blockchain-interaction-service
vsl-blockchain-service
vsl-user-service
wasmApp
Web3AuthDemo
Web3AuthDemo2
webApp
YapilyDemo
youtube-mcp
youtube-planner
youtube-transcript-mcp
youtube-transcript-mcp-original
Bash Find Graphiti usage in guardkit
IN
find /Users/richardwoollcott/Projects/appmilla_github/guardkit -maxdepth 4 -name "*.py" 2>/dev/null | xargs grep -l "graphiti_core\|Graphiti(" 2>/dev/null | head -20

OUT
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_feature_orchestrator.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_api_call_preview.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_cli_review.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_autobuild_context_integration.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_coach_context_integration.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_pipeline_integration.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_system_plan_e2e.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_system_commands_e2e.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_system_overview_graphiti.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_impact_analysis_graphiti.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/seam/test_system_plan_seams.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/seam/test_orchestrator_wiring.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/seam/test_graphiti_persistence.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/cli/test_init.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/knowledge/test_template_sync.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/knowledge/test_graphiti_client_embedding_preflight.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/knowledge/test_graphiti_client.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/knowledge/test_falkordb_workaround.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/knowledge/test_graphiti_group_prefixing.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/knowledge/test_graphiti_client_embedder_injection.py
Bash Find graphiti src files in guardkit
IN
find /Users/richardwoollcott/Projects/appmilla_github/guardkit/src -name "graphiti*" -o -name "*graphiti*" 2>/dev/null | head -20

OUT
(Bash completed with no output)
Bash Read dgx-spark README
IN
cat /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark/README.md 2>/dev/null | head -80

OUT
# DGX Spark / GB10 Research

Research, decisions, and deployment docs for the GuardKit inference fleet on the Dell DGX Spark GB10 (Blackwell SM121, 128 GB unified memory).

## Current architecture (deployed 2026-04-29)

**All-llama.cpp via llama-swap on :9000.** No vLLM. No Docker for inference. Four models permanently loaded, zero swap overhead.

| Model | Role | Footprint | Port |
|---|---|---|---|
| Qwen2.5-14B Q8_0 | Graphiti entity extraction + Jarvis intent routing | ~22 GB | :9000 (via llama-swap) |
| nomic-embed-text-v1.5 f16 | Embeddings (768 dims) for Graphiti + ChromaDB | ~0.3 GB | :9000 (via llama-swap) |
| Qwen3.6-35B-A3B Q4_K_XL | Workhorse: AutoBuild Player/Coach, Forge, Dataset Factory | ~21 GB | :9000 (via llama-swap) |
| Gemma 4 26B-A4B Q4_K_M | Fine-tuned GCSE study tutor (Socratic method) | ~17 GB | :9000 (via llama-swap) |
| **Total** | | **~60 GB** | **64 GB headroom** |

Production config: `/opt/llama-swap/config/config.yaml`
Systemd service: `llama-swap.service`
Logs: `/opt/llama-swap/logs/llama-swap.log`

## Document index

### Current (active)

| Document | Purpose |
|---|---|
| [**RUNBOOK-v3-production-deployment.md**](./RUNBOOK-v3-production-deployment.md) | Production deployment runbook. Executed 2026-04-28, six gaps found and fixed via TASK-RUN-D6F4, two operational follow-ups resolved via TASK-OPS-7CB1/9F2A. Post-fix runbook is clean-room re-executable. |
| [**llama-swap-systemd-supervision.md**](./llama-swap-systemd-supervision.md) | User-space systemd unit with `-watch-config` for auto-reload. Replaces the orphaned nohup process. Pending: sudo cleanup of stale root unit + `loginctl enable-linger`. |
| [**POST-VALIDATION-model-strategy-revision.md**](./POST-VALIDATION-model-strategy-revision.md) | Strategy pivot from dense 27B to MoE 35B-A3B workhorse. Explains the physics (bandwidth wall) and the decision. |
| [**gb10-model-requirements-matrix.md**](./gb10-model-requirements-matrix.md) | Fleet-wide model consolidation analysis: 16 roles → 6 models → 4 deployed. Speed expectations for the dense 27B are superseded by the post-validation revision but the role mapping and cluster analysis remain valid. |
| [**qwen3.6-27b-gb10-community-research.md**](./qwen3.6-27b-gb10-community-research.md) | Forum research on Qwen3.6-27B, MTP, DFlash, PrismaQuant, DDTree. Benchmark data and deployment recipes. |

### Historical (superseded but preserved)

| Document | Status |
|---|---|
| [llama-swap-setup.md](./llama-swap-setup.md) | **Superseded by RUNBOOK-v3.** Describes the old vLLM proxy + Coder-Next/GPT-OSS swap architecture. Kept for reference on llama.cpp build flags, dynamic VRAM launcher, and LiteLLM Phase 4 config. |
| [llama-swap-config.yaml](./llama-swap-config.yaml) | **Superseded.** Old config with vLLM proxy entries. Production config is now at `/opt/llama-swap/config/config.yaml` on the GB10. |
| [dark-factory-economics-and-model-serving.md](./dark-factory-economics-and-model-serving.md) | Original research doc. Historical context on the cost crisis, forum research, and DECISION-DF-001. Conclusions about model choices are superseded. |
| [dark-factory-dataset-factory-conversation-starter.md](./dark-factory-dataset-factory-conversation-starter.md) | Original conversation starter for the dataset factory session. Historical. |

### Validation records

| Document | What it proved |
|---|---|
| [**RESULTS-v3-production-deployment.md**](./RESULTS-v3-production-deployment.md) | Production deployment results: 65 GB VRAM, 41.32 tok/s workhorse, all four models coexisting. Six gaps found and documented. |
| [**VALIDATION-D6F4-gap-fix-results.md**](./VALIDATION-D6F4-gap-fix-results.md) | All six D6F4 gaps verified PASS against live deployment. Surfaced two operational follow-ups (overnight crashes + 429 throttling). |
| [**VALIDATION-OPS-7CB1-9F2A-results.md**](./VALIDATION-OPS-7CB1-9F2A-results.md) | Keep-alive timer revives crashed children in 30s (TASK-OPS-7CB1). Concurrency tuning eliminated 429 throttling: 0 rate limits vs 8 yesterday (TASK-OPS-9F2A). Both fixes installed and active on host. |
| [RESULTS-v2-all-llamacpp-validation.md](./RESULTS-v2-all-llamacpp-validation.md) | All-llama.cpp architecture works: Graphiti JSON extraction via llama.cpp (no xgrammar needed), embeddings at 768 dims, MoE workhorse at 45 tok/s, three-model co-existence at 46 GB. **The key evidence that eliminated vLLM.** |
| [RESULTS-qwen3.6-27b-validation.md](./RESULTS-qwen3.6-27b-validation.md) | Dense Qwen3.6-27B quality is excellent (tool calling, JSON, reasoning all pass) but hits 8.35 tok/s bandwidth wall on GB10. **The key evidence that pivoted to MoE.** |
| [RUNBOOK-v2-all-llamacpp-architecture.md](./RUNBOOK-v2-all-llamacpp-architecture.md) | The validation runbook for RESULTS-v2. |
| [RUNBOOK-qwen3.6-27b-validation.md](./RUNBOOK-qwen3.6-27b-validation.md) | The validation runbook for RESULTS-v1. |

### Background reading

| Document | Notes |
|---|---|
| `DGX Spark, Nemotron3, and NVFP4 - Thomas P. Braun.pdf` | NVFP4 optimisation background |

## Key decisions made during this research

1. **DECISION-DF-001:** No cloud API on dark factory critical path (triggered by £30 Gemini spend in 3 days)
2. **Dense 27B → MoE 35B-A3B:** Memory-bandwidth physics means dense models hit ~8-10 tok/s ceiling on GB10; MoE with 3B active params achieves 45+ tok/s
3. **vLLM → all-llama.cpp:** vLLM pre-allocates ~50 GB for a 14 GB model; llama.cpp takes only what it needs, reclaiming ~36 GB
4. **Four always-loaded models:** At ~60 GB total, no swapping is needed — everything stays hot with 64 GB headroom

## External references

- [NVIDIA DGX Spark / GB10 forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719)
- [Spark Arena leaderboard](https://spark-arena.com/leaderboard)
- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap)
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
- [AEON-7 DFlash deployment](https://github.com/AEON-7/Qwen3.6-NVFP4-DFlash) — reference for future DFlash integration
- [martinB78's full-stack repo](https://github.com/mARTin-B78/dgx-spark_lite-llm_llama-swap_vllm_llama-cpp_ollama)

## Rollback

If the all-llama.cpp architecture needs to be reverted:
```bash
sudo systemctl stop llama-swap
Bash Locate guardkit graphiti client
IN
find /Users/richardwoollcott/Projects/appmilla_github/guardkit/src -type d -name "*graphiti*" -o -name "*knowledge*" 2>/dev/null | head; echo "---"; find /Users/richardwoollcott/Projects/appmilla_github/guardkit -maxdepth 5 -name "graphiti_client.py" 2>/dev/null; echo "---"; find /Users/richardwoollcott/Projects/appmilla_github/guardkit/src -maxdepth 5 -type f -name "*.py" 2>/dev/null | xargs grep -l "Graphiti(" 2>/dev/null | head

OUT
---
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py
---
Bash List guardkit knowledge module
IN
ls /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/ 2>/dev/null

OUT
__init__.py
__pycache__
adr_discovery.py
adr_service.py
adr.py
autobuild_context_loader.py
budget_calculator.py
config.py
context_formatter.py
context_loader.py
decision_detector.py
entities
episode_splitting.py
facts
failed_approach_manager.py
falkordb_workaround.py
feature_detector.py
feature_plan_context.py
gap_analyzer.py
graphiti_client.py
interactive_capture.py
job_context_retriever.py
outcome_manager.py
outcome_queries.py
project_seeding.py
quality_gate_formatter.py
query_logger.py
relevance_tuning.py
review_knowledge_capture.py
role_constraint_formatter.py
seed_agents.py
seed_architecture_decisions.py
seed_command_workflows.py
seed_component_status.py
seed_failed_approaches.py
seed_failure_patterns.py
seed_feature_build_adrs.py
seed_feature_build_architecture.py
seed_feature_overviews.py
seed_helpers.py
seed_integration_points.py
seed_pattern_examples.py
seed_patterns.py
seed_product_knowledge.py
seed_project_architecture.py
seed_project_overview.py
seed_quality_gate_phases.py
seed_role_constraints.py
seed_rules.py
seed_technology_stack.py
seed_templates.py
seeding.py
system_seeding.py
task_analyzer.py
template_pattern_loader.py
template_sync.py
turn_state_operations.py
Bash Size of guardkit graphiti_client.py
IN
wc -l /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py 2>/dev/null

OUT
    2496 /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py
Bash Read graphiti yaml endpoint migration task
IN
cat /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md 2>/dev/null | head -120

OUT
# Task: Update graphiti.yaml Endpoints — vLLM → llama-swap

**Date:** 2026-04-29
**Context:** The GB10 inference stack has been migrated from vLLM to all-llama.cpp via llama-swap on `:9000` (see `guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md`). The `guardkit` repo's config was updated during deployment. All other repos still point at the dead vLLM endpoints (`:8000` for LLM, `:8001` for embeddings).

---

## What Needs to Change

In every `.guardkit/graphiti.yaml` file:

| Field | Old (vLLM, dead) | New (llama-swap, live) |
|---|---|---|
| `llm_base_url` | `http://promaxgb10-41b1:8000/v1` | `http://promaxgb10-41b1:9000/v1` |
| `embedding_base_url` | `http://promaxgb10-41b1:8001/v1` | `http://promaxgb10-41b1:9000/v1` |

Additionally, add this field if missing (prevents 429 throttling — see TASK-OPS-9F2A):
```yaml
chunk_extraction_concurrency: 4
```

And remove the deprecated fields at the bottom if present:
```yaml
# REMOVE these:
host: localhost
port: 8000
```

The `llm_model` value `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` is fine — it's registered as a llama-swap alias for `qwen-graphiti`.

---

## Affected Repos (13 repos, 15 files)

### ✅ Already updated
| Repo | Status |
|---|---|
| `guardkit` | ✅ Updated to :9000 during v3 deployment |

### ❌ Needs update — Active repos (create tasks for these)

| # | Repo | File | Priority |
|---|---|---|---|
| 1 | `agentic-dataset-factory` | `.guardkit/graphiti.yaml` | **High** — active pipeline work |
| 2 | `jarvis` | `.guardkit/graphiti.yaml` | **High** — fleet intent router |
| 3 | `forge` | `.guardkit/graphiti.yaml` | **High** — pipeline orchestrator |
| 4 | `study-tutor` | `.guardkit/graphiti.yaml` | **High** — Lilymay's tutor |
| 5 | `specialist-agent` | `.guardkit/graphiti.yaml` | **High** — agent fleet member |
| 6 | `lpa-platform` | `.guardkit/graphiti.yaml` | **Medium** — FinProxy client project |
| 7 | `nats-core` | `.guardkit/graphiti.yaml` | **Medium** — fleet messaging |
| 8 | `nats-infrastructure` | `.guardkit/graphiti.yaml` | **Medium** — fleet infra |
| 9 | `require-kit` | `.guardkit/graphiti.yaml` | **Medium** — PM tooling |
| 10 | `youtube-transcript-mcp` | `.guardkit/graphiti.yaml` | **Low** — content pipeline |

### ❌ Needs update — Reference/exemplar repos (lower priority)

| # | Repo | File | Priority |
|---|---|---|---|
| 11 | `deepagents-player-coach-exemplar` | `.guardkit/graphiti.yaml` | **Low** — template source |
| 12 | `deepagents-player-coach-exemplar-original` | `.guardkit/graphiti.yaml` | **Low** — archive |
| 13 | `dotnet-functional-fastendpoints-exemplar` | `.guardkit/graphiti.yaml` | **Low** — .NET reference |
| 14 | `vllm-profiling` | `.guardkit/graphiti.yaml` | **Low** — historical |

### Worktree copies (updated automatically when parent is fixed)

| Repo | Worktree file |
|---|---|
| `study-tutor` | `.guardkit/worktrees/FEAT-1773/.guardkit/graphiti.yaml` |
| `vllm-profiling` | `.guardkit/worktrees/FEAT-1637/.guardkit/graphiti.yaml` |

### Different schema — no action needed

| Repo | File | Notes |
|---|---|---|
| `require-kit` | `installer/global/config/graphiti.yaml` | This is the RequireKit installer template — uses Neo4j/Bolt config, not LLM endpoints. Not affected. |

---

## Task Template (copy per repo)

```
Title: Update graphiti.yaml — vLLM → llama-swap endpoint migration

The GB10 inference stack has migrated from vLLM (ports 8000/8001) to 
all-llama.cpp via llama-swap (single port 9000). Update the Graphiti 
config to point at the live endpoint.

Changes in .guardkit/graphiti.yaml:
1. llm_base_url: change :8000 → :9000
2. embedding_base_url: change :8001 → :9000  
3. Add chunk_extraction_concurrency: 4 (if missing)
4. Remove deprecated host/port fields at bottom (if present)
5. Update comments: "vLLM" → "llama-swap" where applicable

Reference: guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md
```

---

## Batch Fix Script (optional — run from MacBook)

If you'd prefer to fix all 13 repos in one shot rather than creating individual tasks:

```bash
cd ~/Projects/appmilla_github

for REPO in \
    agentic-dataset-factory \
    jarvis \
    forge \
    study-tutor \
    specialist-agent \
    lpa-platform \
    nats-core \
    nats-infrastructure \
    require-kit \
    youtube-transcript-mcp \
    deepagents-player-coach-exemplar \
    deepagents-player-coach-exemplar-original \
    dotnet-functional-fastendpoints-exemplar \
Update Todos

Investigate guardkit's graphiti_client.py + config + embedder/LLM wiring

Check study-tutor's existing .guardkit/graphiti.yaml config

Check specialist-agent's Graphiti integration shape

Rewrite TASK-PH2-GR-001 to require local-only (llama-swap) and reuse guardkit patterns

Propose follow-up task: extract Graphiti core lib to shared package

Commit task updates
Bash Read study-tutor's graphiti.yaml
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/graphiti.yaml 2>/dev/null && cat /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/graphiti.yaml

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/graphiti.yaml
project_id: study_tutor
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
max_concurrent_episodes: 3
chunk_extraction_concurrency: 4
# --- Primary: GB10 vLLM — re-enable when GB10 is free ---
#llm_provider: vllm
#llm_base_url: http://promaxgb10-41b1:9000/v1
#llm_model: qwen-graphiti
# --- Active: MacBook Pro M2 Max (Ollama, Q4_K_M) — GB10 busy with dataset factory ---
llm_provider: ollama
llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:9000/v1
embedding_model: nomic-embed
# Embedding dimension is resolved from KNOWN_EMBEDDING_DIMS
# based on embedding_model above. Set explicitly only to override
# (e.g., for Matryoshka truncation).
group_ids:
- product_knowledge
- command_workflows
- architecture_decisions
Bash Read guardkit's canonical graphiti.yaml
IN
cat /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml 2>/dev/null

OUT
# Graphiti Knowledge Graph Configuration
#
# This file configures the Graphiti integration for GuardKit.
# FalkorDB runs on the Synology DS918+ NAS, accessible via Tailscale.
#
# LLM Endpoint Switching:
#   To switch between GB10 and MacBook LLM, toggle the llm_provider/llm_base_url/
#   llm_model settings below. See docs/reference/graphiti-macbook-offload.md for
#   full setup instructions and the toggle script.
#
# All settings can be overridden via environment variables:
#   - GRAPHITI_ENABLED: Enable/disable integration
#   - GRAPH_STORE: Graph backend ('falkordb' or 'neo4j')
#   - FALKORDB_HOST: FalkorDB host
#   - FALKORDB_PORT: FalkorDB port
#   - GRAPHITI_TIMEOUT: Connection timeout in seconds
#
# FalkorDB on NAS:
#   ssh richardwoollcott@whitestocks
#   cd /volume1/guardkit/docker
#   sudo docker-compose -f docker-compose.falkordb.yml up -d
#
# FalkorDB Browser UI: http://whitestocks:3000

# Project ID for namespace prefixing
# This ensures knowledge persists across directory moves/renames
project_id: guardkit

# Enable Graphiti integration (set to false to disable)
enabled: true

# Graph database backend
graph_store: falkordb

# FalkorDB connection (Synology DS918+ NAS via Tailscale)
falkordb_host: whitestocks
falkordb_port: 6379

# Connection settings
timeout: 30.0

# Maximum concurrent episode creation calls during init seeding.
# Bounds asyncio.gather parallelism to avoid LLM rate limits.
# Range: 1-10 (1 = sequential, 3 = default)
max_concurrent_episodes: 3

# Maximum parallel entity-extraction LLM calls per episode.
# Sets graphiti-core's SEMAPHORE_LIMIT env var inside `add-context`.  When a
# large doc is split into many chunks (full_doc parser), each add_episode()
# fires several /v1/chat/completions calls in parallel for entity/edge
# extraction.  This value caps that fan-out.
#
# MUST stay <= the upstream LLM server's per-model concurrency cap.
#   - For llama-swap on DGX Spark: match the qwen-graphiti model's
#     `concurrencyLimit` in /opt/llama-swap/config/config.yaml.
#     Currently 4 → set this to 4 (or 8 if both bumped together).
#   - For vLLM: match the model's --max-num-seqs.
# Setting this too high triggers HTTP 429 throttling and causes the OpenAI
# client to back-off + retry — operation succeeds but wall-time multiplies
# and logs fill with "Retrying request" / "Rate limit exceeded" warnings.
# Range: 1-20 (5 = default)
# Background: TASK-OPS-9F2A
chunk_extraction_concurrency: 4

# LLM provider for Graphiti entity extraction
# Options: openai (default), vllm, ollama, gemini
#
# GB10 local vLLM (FP8) — default. Free; no per-request cost.
# Switch to Gemini only while GB10 is busy training (see fallback below).
# Cost note (2026-04-20): Gemini 2.5 Pro accumulated ~£10/day during normal
# Graphiti ingestion. See: .guardkit/llm-provider-switching.md (this repo).
#
# --- GB10 (vLLM, FP8) — ACTIVE ---
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:9000/v1
llm_model: qwen-graphiti
#
# --- Fallback: Google Gemini (cloud, paid) — uncomment when GB10 training ---
# Requires GOOGLE_API_KEY env var and `pip install guardkit-py[gemini]`.
#llm_provider: gemini
#llm_model: gemini-2.5-pro
#
# --- Fallback: MacBook Pro M2 Max (Ollama, Q4_K_M) ---
#llm_provider: ollama
#llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
#llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096  # Cap output tokens; prevents 16384 default exceeding 32K context (TASK-REV-84A7)

# Embedding provider for Graphiti vector search
# Options: openai (default), vllm, ollama
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:9000/v1

# Embedding model for semantic search
# Supported by openai, vllm, and ollama providers
embedding_model: nomic-embed

# Embedding dimension is resolved from KNOWN_EMBEDDING_DIMS
# based on embedding_model above. Set explicitly only to override
# (e.g., for Matryoshka truncation).

# Group IDs for organizing knowledge
# These create separate namespaces in the knowledge graph
group_ids:
  - product_knowledge      # Domain concepts, entities, relationships
  - command_workflows      # GuardKit command patterns and usage
  - architecture_decisions # ADRs and design rationale

# Deprecated fields (kept for backwards compatibility)
host: localhost
Read graphiti_client.py (lines 2-121)
Bash Find LLM/embedder construction in guardkit graphiti_client
IN
grep -n "def _build_llm_client\|def _build_embedder\|def _build_cross_encoder\|llm_provider == \|OpenAIClient\|GeminiClient\|OpenAIEmbedder\|cross_encoder\|llm_client=\|embedder=" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py | head -40

OUT
571:    def _build_embedder(self):
575:            An OpenAIEmbedder configured for the local inference endpoint,
580:        from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
591:        return OpenAIEmbedder(config=OpenAIEmbedderConfig(**embedder_kwargs))
593:    def _build_llm_client(self):
597:            A GeminiClient for 'gemini' provider, or an OpenAIGenericClient for
601:        if self.config.llm_provider == "openai":
604:        if self.config.llm_provider == "gemini":
606:            from graphiti_core.llm_client.gemini_client import GeminiClient
613:            return GeminiClient(
829:            self.config.llm_provider == "openai"
Read graphiti_client.py (lines 561-680)
Bash Find cross-encoder handling in guardkit
IN
grep -n "cross_encoder\|CrossEncoder" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py | head -15

OUT
(Bash completed with no output)
Bash Find Graphiti() construction site
IN
grep -n "Graphiti(" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py | head

OUT
762:                test_graphiti = Graphiti(graph_driver=driver)
764:                test_graphiti = Graphiti(
874:                self._graphiti = Graphiti(graph_driver=driver, **extra_kwargs)
876:                self._graphiti = Graphiti(
Read graphiti_client.py (lines 821-910)
Bash GraphitiConfig surface
IN
grep -n "class GraphitiConfig\|llm_provider:\|llm_base_url:\|llm_model:\|embedding_provider:\|embedding_base_url:\|embedding_model:\|embedding_dimensions\|llm_max_tokens\|falkordb_host\|chunk_extraction_concurrency" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py | head -30

OUT
135:class GraphitiConfig:
149:        falkordb_host: FalkorDB host for connection
153:        llm_provider: LLM provider for entity extraction ('openai', 'vllm', 'ollama', 'gemini')
154:        llm_base_url: LLM provider base URL (required for vllm/ollama; ignored for gemini)
155:        llm_model: LLM model name (e.g., 'Qwen/Qwen3-Coder-30B-A3B', 'gemini-2.5-flash')
156:        embedding_provider: Embedding provider ('openai', 'vllm', 'ollama')
157:        embedding_base_url: Embedding provider base URL (required for vllm/ollama)
158:        embedding_model: Embedding model name (e.g., 'text-embedding-3-small')
159:        embedding_dimensions: Explicit embedding vector dimensions (optional). When set,
188:    falkordb_host: str = "localhost"
194:    llm_provider: str = "openai"           # "openai" | "vllm" | "ollama" | "gemini"
195:    llm_base_url: Optional[str] = None     # e.g., "http://host:8000/v1"; unused for gemini
196:    llm_model: Optional[str] = None        # e.g., "Qwen/Qwen3-Coder-30B-A3B"
197:    llm_max_tokens: Optional[int] = None   # Cap output tokens (e.g. 4096 for 8192-ctx models)
198:    embedding_provider: str = "openai"     # "openai" | "vllm" | "ollama"
199:    embedding_base_url: Optional[str] = None  # e.g., "http://host:8001/v1"
200:    embedding_model: str = "text-embedding-3-small"
201:    embedding_dimensions: Optional[int] = None  # explicit dimensions (e.g. 1024 for Matryoshka)
215:        if self.llm_provider in ("vllm", "ollama") and not self.llm_base_url:
217:        if self.embedding_provider in ("vllm", "ollama") and not self.embedding_base_url:
589:        if self.config.embedding_dimensions is not None:
590:            embedder_kwargs["embedding_dim"] = self.config.embedding_dimensions
621:        if self.config.llm_max_tokens is not None:
622:            kwargs["max_tokens"] = self.config.llm_max_tokens
632:    async def _check_embedding_dimensions(self) -> None:
664:        # Use explicit embedding_dimensions from config if set; fall back to KNOWN_EMBEDDING_DIMS
665:        if self.config.embedding_dimensions is not None:
666:            expected_dim = self.config.embedding_dimensions
759:                    host=self.config.falkordb_host,
869:                    host=self.config.falkordb_host,
Bash Read llama-swap config (model aliases)
IN
cat /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark/llama-swap-config.yaml 2>/dev/null | head -60

OUT
# llama-swap config for the GuardKit dark factory on GB10
# =========================================================
# Single front door at :9000 serving all agents.
# - Forever group: Graphiti LLM + embeddings (delegated to existing vLLM services)
# - Builders group: AutoBuild Coder + Jarvis/Architect/Coach reasoner (swap)
#
# All endpoints: OpenAI /v1/chat/completions, /v1/embeddings
#                Anthropic /v1/messages, /v1/messages/count_tokens
# Route by the "model" field in each request.
#
# Reference: docs/research/dgx-spark/llama-swap-setup.md

healthCheckTimeout: 600          # 10 min — GPT-OSS 120B cold-load can take ~4 min
globalTTL: 1800                  # 30 min idle → unload swap members
startPort: 5800                  # llama-swap auto-assigns internal ports from here
includeAliasesInList: true
logLevel: info

# Uncomment to require API key for all requests
# apiKeys:
#   - "${env.LLAMASWAP_API_KEY}"

models:
  # ============================================================
  # FOREVER GROUP — delegated to existing vLLM services.
  # Lifecycle managed by existing vllm-graphiti.sh / vllm-embed.sh.
  # llama-swap treats these as external; never starts or stops them.
  # ============================================================

  "qwen-graphiti":
    name: "Graphiti entity extraction (Qwen2.5-14B FP8, delegated to vLLM)"
    proxy: http://127.0.0.1:8000
    checkEndpoint: /health
    ttl: 0
    aliases:
      - "neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic"
      - "graphiti-llm"

  "nomic-embed":
    name: "Embeddings (nomic-embed-text-v1.5, delegated to vLLM)"
    proxy: http://127.0.0.1:8001
    checkEndpoint: /health
    ttl: 0
    aliases:
      - "nomic-embed-text-v1.5"
      - "nomic-ai/nomic-embed-text-v1.5"
      - "embeddings"

  # ============================================================
  # BUILDERS GROUP — llama.cpp-managed, swap as needed.
  # Native /v1/messages support for Claude Agent SDK (AutoBuild).
  # ============================================================

  "qwen-coder-next":
    name: "AutoBuild Player (Qwen3-Coder-Next FP8)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/qwen3-coder-next/Qwen3-Coder-Next-FP8.gguf
Bash Check specialist-agent graphiti shape
IN
find /Users/richardwoollcott/Projects/appmilla_github/specialist-agent -maxdepth 5 -name "graphiti*" -o -name "*graphiti*.yaml" 2>/dev/null | head; echo "---"; cat /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.guardkit/graphiti.yaml 2>/dev/null | head -40

OUT
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.guardkit/graphiti-query-log.jsonl.1
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.guardkit/graphiti-query-log.jsonl
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.guardkit/graphiti.yaml
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/features/graphiti-query-tool
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/tasks/backlog/graphiti-query-tool
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/features/graphiti-query-tool/graphiti-query-tool_assumptions.yaml
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/features/graphiti-query-tool/graphiti-query-tool_summary.md
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/features/graphiti-query-tool/graphiti-query-tool.feature
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/research/ideas/graphiti-seeding-instructions.md
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_query.py
---
project_id: specialist_agent
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
max_concurrent_episodes: 3
chunk_extraction_concurrency: 4
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:9000/v1
llm_model: qwen-graphiti
# --- Fallback: MacBook Pro M2 Max (Ollama, Q4_K_M) — uncomment if GB10 offline ---
#llm_provider: ollama
#llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
#llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:9000/v1
embedding_model: nomic-embed
# Embedding dimension is resolved from KNOWN_EMBEDDING_DIMS
# based on embedding_model above. Set explicitly only to override
# (e.g., for Matryoshka truncation).
group_ids:
- product_knowledge
- command_workflows
- architecture_decisions
Bash Find specialist-agent graphiti src
IN
find /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src -name "graphiti_client.py" 2>/dev/null; echo "---"; grep -rln "from graphiti_core\|import graphiti_core\|Graphiti(" /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src 2>/dev/null | head

OUT
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py
---
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py
Bash Confirm placeholder api_key pattern
IN
grep -n "OpenAIGenericClient\|OpenAIEmbedder\|api_key=\"local\|local-key" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py | head

OUT
575:            An OpenAIEmbedder configured for the local inference endpoint,
580:        from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
584:            api_key="local-key",  # Local inference ignores API key; placeholder required
591:        return OpenAIEmbedder(config=OpenAIEmbedderConfig(**embedder_kwargs))
597:            A GeminiClient for 'gemini' provider, or an OpenAIGenericClient for
619:        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
623:        return OpenAIGenericClient(
627:                api_key="local-key",  # Local inference ignores API key; placeholder required
Bash Specialist-agent graphiti client header
IN
wc -l /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py 2>/dev/null; echo "---"; head -30 /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py 2>/dev/null

OUT
     459 /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py
---
"""Graphiti async client wrapper with lazy initialisation and graceful degradation.

TASK-GQT-001: Core client with lazy init, monkey-patches, timeout enforcement.
TASK-GQT-004: Graceful degradation — circuit breaker, safe query methods,
              health check. When Graphiti/FalkorDB is unavailable, safe methods
              return empty lists instead of raising, allowing the Player to
              continue generation without knowledge graph context.

All ``graphiti-core`` and ``guardkit`` imports are lazy (inside methods)
so the module loads successfully even when these packages are not installed.

Usage::

    config = GraphitiConnectionConfig(falkordb_host="localhost", falkordb_port=6379)
    async with GraphitiQueryClient(config=config) as client:
        # Raising methods (original contract):
        nodes = await client.search_nodes("auth patterns", group_ids=["project:myapp"])

        # Non-raising methods (graceful degradation):
        nodes = await client.search_nodes_safe("auth patterns", group_ids=["project:myapp"])
        facts = await client.search_facts_safe("decisions", group_ids=["project:myapp"])

    # Health check (no side effects):
    available = await is_graphiti_available(config)
"""

from __future__ import annotations

import asyncio
import logging
Bash Check shared client + import availability
IN
grep -rln "guardkit.knowledge.graphiti_client\|from guardkit" /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src 2>/dev/null | head -5; echo "---import test---"; /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python -c "from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient; from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig; print('importable')"

OUT
/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py
---import test---
importable
I have what I need. Now rewriting TASK-PH2-GR-001 around the GuardKit canonical pattern + local-only constraint, and adding a follow-up task for extracting the shared library.

Write TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
191 lines
---
id: TASK-PH2-GR-001
title: Graphiti runtime integration repair — wire local LLM + embedder via llama-swap (no cloud APIs)
task_type: feature
parent_validation: phase-1-validation.md
phase: 2
implementation_mode: design-first
complexity: 5
estimated_minutes: 240
status: backlog
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
dependencies: []
blocks:
- FEAT-PH2-001
related:
- TASK-PH2-GR-002
- guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md
tags:
- graphiti
- llm-wiring
- embedder
- llama-swap
- local-only
- no-cloud-api
- dark-factory
- phase-1-falsification-repair
- runtime-integration
- ahead-of-FEAT-PH2-001
---

# Graphiti runtime integration repair

## Why this exists

Phase 1 close-out gate (`docs/research/ideas/phase-1-validation.md`) falsified G2/G3/G4/G5/G6/G13. Root cause: [`src/study_tutor/knowledge/graphiti_client.py:get_client(config)`](../../src/study_tutor/knowledge/graphiti_client.py) constructs `Graphiti(graph_driver=driver)` with **no `llm_client`, no `embedder`, no `cross_encoder`**, so graphiti-core 0.29 defaults all three to OpenAI clients keyed off `OPENAI_API_KEY` (`not_needed` placeholder) and 401s on every `add_episode`. The Phase 1 autobuild stayed green because every graphiti test mocks the integration; nothing in `tests/` ever booted a real `Graphiti` instance.

This task is the Phase 2 leading task — must land **before** FEAT-PH2-001 spec + plan because gamification reads `get_student_state` and writes `GamificationState` through the same client path.

## Hard constraints

### No cloud LLM/embedding APIs on the critical path (DECISION-DF-001)

Per [`guardkit/docs/research/dgx-spark/README.md`](../../../guardkit/docs/research/dgx-spark/README.md): _"DECISION-DF-001: No cloud API on dark factory critical path (triggered by £30 Gemini spend in 3 days)."_ All Graphiti LLM and embedding traffic must hit the local GB10 fleet, not OpenAI/Gemini/Anthropic. The earlier draft of this task mentioned wiring `GeminiClient` as the LLM — **rescinded**. Cloud providers are off-limits even as fallbacks unless explicitly approved per-task.

### All inference goes through llama-swap on `:9000`

The DGX Spark stack was migrated 2026-04-29 from vLLM (ports 8000/8001) to all-llama.cpp via llama-swap on a single port `:9000`. Reference: [`guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md`](../../../guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md). Models accessed via llama-swap aliases:

| Alias | Model | Role |
|---|---|---|
| `qwen-graphiti` | Qwen2.5-14B-Instruct FP8 | Graphiti entity extraction (the LLM `add_episode` calls) |
| `nomic-embed` | nomic-embed-text-v1.5 (768 dims) | Embeddings for Graphiti + ChromaDB |

Endpoint: `http://promaxgb10-41b1:9000/v1` (Tailscale hostname). Single OpenAI-compatible interface for both LLM and embedder.

### Use the GuardKit-canonical wiring pattern

GuardKit has the solved 2496-line client at [`guardkit/guardkit/knowledge/graphiti_client.py`](../../../guardkit/guardkit/knowledge/graphiti_client.py). The two key methods to mirror:

- `_build_llm_client()` — for `vllm`/`ollama` providers, returns
  ```python
  OpenAIGenericClient(
      config=LLMConfig(
          base_url=config.llm_base_url,
          model=config.llm_model,
          api_key="local-key",  # placeholder; local inference ignores it
      ),
      max_tokens=config.llm_max_tokens,
  )
  ```
- `_build_embedder()` — for `vllm`/`ollama` providers, returns
  ```python
  OpenAIEmbedder(
      config=OpenAIEmbedderConfig(
          base_url=config.embedding_base_url,
          embedding_model=config.embedding_model,
          api_key="local-key",
          embedding_dim=config.embedding_dimensions,  # only when explicit
      ),
  )
  ```

Both `OpenAIGenericClient` and `OpenAIEmbedder` ship with the base `graphiti-core` install (already installed in the study-tutor venv after the close-out repair sweep — no new pip extras needed for local-only operation).

`cross_encoder` is left as graphiti-core's default. `add_episode` does not invoke it (it only matters for search reranking); searches in study-tutor go through `EntityNode.get_by_group_ids` / `EntityEdge.get_by_group_ids` which bypass reranking too. If reranking is ever needed downstream, raise a follow-up task — do **not** wire OpenAI's default reranker.

### Read config from `.guardkit/graphiti.yaml`

study-tutor already has [`/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/graphiti.yaml`](../../.guardkit/graphiti.yaml) with the GuardKit-canonical schema (same shape across guardkit, study-tutor, specialist-agent, jarvis, forge, etc.). Current values:

```yaml
project_id: study_tutor
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
max_concurrent_episodes: 3
chunk_extraction_concurrency: 4
# Active: MacBook Pro M2 Max (Ollama, Q4_K_M) — GB10 busy with dataset factory
llm_provider: ollama
llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:9000/v1
embedding_model: nomic-embed
group_ids: [product_knowledge, command_workflows, architecture_decisions]
```

The current `llm_provider: ollama` (MacBook fallback) is fine for an immediate seed run. Once GB10 is free, the commented-out `llm_provider: vllm` block at the top should be re-enabled (single-line config swap; no code change). **Do not** uncomment the Gemini fallback that exists in `guardkit/.guardkit/graphiti.yaml` — that's GuardKit's choice for its own knowledge graph, not ours, and conflicts with DECISION-DF-001 for study-tutor's runtime.

The Phase-1 `GraphitiConnectionConfig` Pydantic model in [`graphiti_client.py:62-90`](../../src/study_tutor/knowledge/graphiti_client.py#L62-L90) has a different schema (uses `falkor_host`, `embedder_url`, no `llm_provider` switch). Two ways to bridge:

1. **Loader path** — add a `GraphitiConfig.from_yaml(".guardkit/graphiti.yaml")` classmethod that reads the canonical YAML and projects into the runtime model. Keeps the runtime model isolated; YAML is the source of truth.
2. **Schema-replace path** — replace `GraphitiConnectionConfig` with the GuardKit-canonical 13-field config dataclass directly. Cleaner long-term but bigger blast radius (migrates the field names referenced throughout `get_client`, `seed_student_model.py`, tests).

Recommended: **Loader path** for this repair task (smallest blast radius, unblocks Lilymay seed today). Schema unification deferred to TASK-PH2-GR-002 (shared Graphiti core lib).

## Acceptance criteria

1. **AC-001 — Local LLM client wired via `OpenAIGenericClient`.** `get_client()` constructs an `OpenAIGenericClient` for `llm_provider in ("vllm", "ollama")` using the canonical pattern from `guardkit/guardkit/knowledge/graphiti_client.py:_build_llm_client`. `api_key="local-key"` (placeholder). `OPENAI_API_KEY` is **never** read by this code path. Per DECISION-DF-001, `llm_provider == "openai"` and `llm_provider == "gemini"` are not supported in the study-tutor runtime — raise `ValueError("cloud LLM providers disabled per DECISION-DF-001")` with a structured log line at config-load time if either is configured.
2. **AC-002 — Local embedder wired via `OpenAIEmbedder`.** `get_client()` constructs an `OpenAIEmbedder` for `embedding_provider in ("vllm", "ollama")` using the canonical pattern from `guardkit/guardkit/knowledge/graphiti_client.py:_build_embedder`. Same `api_key="local-key"`. Same DECISION-DF-001 enforcement on `embedding_provider == "openai"`.
3. **AC-003 — Cross-encoder left as graphiti-core default.** Documented inline that `add_episode` does not invoke the reranker; if a future search path needs reranking, a follow-up task wires a local cross-encoder. **Do not** ship the cross-encoder defaulted to OpenAI silently — add an init-time guard that logs `WARN: cross_encoder defaulted to graphiti-core internal; reranker calls would hit OpenAI` and treat any cross-encoder use at runtime as a critical error.
4. **AC-004 — Config loaded from `.guardkit/graphiti.yaml`.** New helper `load_graphiti_config_from_yaml(path: Path = Path(".guardkit/graphiti.yaml")) -> GraphitiConnectionConfig` projects the YAML into the runtime model. Fields used: `falkordb_host`, `falkordb_port`, `timeout`, `llm_provider`, `llm_base_url`, `llm_model`, `llm_max_tokens`, `embedding_provider`, `embedding_base_url`, `embedding_model`, `embedding_dimensions` (when present), `chunk_extraction_concurrency`. Env-var overrides honoured for the standard set (`FALKORDB_HOST`, `FALKORDB_PORT`, `GRAPHITI_ENABLED`, etc.) per the YAML's documented contract. The seed script and `tutor_session_*` MCP handlers both load via this helper rather than hand-constructing `GraphitiConnectionConfig`.
5. **AC-005 — Live-graphiti smoke test.** New `tests/smoke/test_graphiti_live_smoke.py` (or equivalent) boots a real `Graphiti` instance with the wired LLM + embedder against either (a) a stubbed driver, or (b) a live FalkorDB if `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1` is set. Round-trips one `add_episode(group_id="student-test", ...)` → `EntityNode.get_by_group_ids(...)` → asserts the episode is reachable. The test fails loudly if either client construction skips the local-endpoint config (defaults regress to OpenAI). The CC-13 regex audit (single `add_episode(` call site in `src/`) continues to pass.
6. **AC-006 — `python scripts/seed_student_model.py` lands Lilymay's baseline against live Synology FalkorDB.** All 25 entity writes succeed. `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns the Student entity with the expected attributes. `get_student_state(client, "lilymay")` returns a non-empty `StudentState` (year_group=11, target_grade="8", non-empty subjects, non-empty topic_confidences). Re-running is idempotent (`event=seeding_skipped`).
7. **AC-007 — End-to-end demo session via MCP runs at least once.** `tutor_start_session` → 5–7× `tutor_turn` → `tutor_session_end` from Claude Desktop, with at least one Coach revision observed and a `session_completed` episode written to Graphiti and visible via `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])`. This unblocks Phase 1 G3/G4/G5/G6/G13. Capture turn p50/p95 latency in `phase-1-validation.md`.
8. **AC-008 — `phase-1-validation.md` updated.** The five falsified items (G2, G3, G4, G5, G6, G13) flip from "Falsified" to "Held" with the live evidence inline. Phase 1 is then structurally complete on its own terms.

## Out of scope

- **Coach calibration pass.** Separate Phase 2 nice-to-have. The repair only needs the runtime to work; it doesn't need the Coach to be optimally tuned.
- **Multi-student support.** Single-student (Lilymay) is the Phase 1+2 invariant.
- **Index migration.** If FalkorDB has stale indices from earlier seed attempts, the `Connection closed by server` warnings during `build_indices_and_constraints` are background-task noise. Investigate only if they escalate into actual write failures after the LLM/embedder fixes land.
- **Adding gamification fields to `tutor_session_end`.** That's FEAT-PH2-001 item 4 and stays in FEAT-PH2-001's own subtask list.
- **Extracting the shared Graphiti core library.** That's `TASK-PH2-GR-002` (separate task — see `tasks/backlog/TASK-PH2-GR-002-extract-shared-graphiti-core-lib.md`). This repair task ships the in-repo wiring; the extraction task is the longer-term debt-reduction follow-up.
- **Cloud LLM/embedder fallbacks.** Not allowed per DECISION-DF-001.

## Already-fixed-in-flight (committed 2026-05-02 — `a210472`, `78d3498`, `732672c`)

These three patches landed during the close-out gate run on 2026-05-02. They're prerequisites for this task — both because they're on the same call path and because they're standalone API-correctness wins regardless of the LLM-wiring outcome.

- **Read API**: `queries.py:_read_student_partition` seam now calls `EntityNode.get_by_group_ids` / `EntityEdge.get_by_group_ids` on the driver, with a duck-typed shortcut for legacy `search_nodes`/`search_memory_facts` test mocks. `GroupsNodesNotFoundError` / `GroupsEdgesNotFoundError` swallowed (bootstrap case).
- **Write API**: `async_write.py:_add_episode_kwargs` builds graphiti-core 0.29's real signature: `source=EpisodeType.json`, `source_description=f"flush:{flush_id}:{name}"`, `reference_time=now()`, `group_id=group_ids[0]` (singular). Flush-id audit string still rides into structured logs unchanged.
- **Group-id format**: `student:` → `student-`, `subject:` → `subject-`, `fleet:appmilla` → `fleet-appmilla` (graphiti-core 0.29's `GroupIdValidationError` rejects characters outside `[A-Za-z0-9_-]`). Constants in `student_model.py` updated; module docstring updated; cross-repo divergence note preserved; tests updated.

Tests at 695/696 (the one failure is a pre-existing dev-machine `mypy`-on-system-Python env issue from FEAT-PH1-002, not introduced here).

**Note on the cross-repo group-id namespace.** The `.guardkit/graphiti.yaml` uses `group_ids: [product_knowledge, command_workflows, architecture_decisions]` — those are the **GuardKit tooling's** group IDs (for its own knowledge graph about the project). The study-tutor **runtime** uses different group ids (`student-lilymay`, `subject-aqa-8702-eng-lit`, `fleet-appmilla`) for its own knowledge graph about the learner. Both sets of writes hit the same FalkorDB; partition isolation is via group_id. This is by design and not a conflict — the AC-004 loader only consumes the connection + LLM/embedder fields from the YAML, not the `group_ids` list (which is GuardKit's surface, not the tutor's).

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| MacBook ollama (current YAML active) is offline at seed time | Low | Low | Toggle YAML to `llm_provider: vllm` pointing at GB10:9000; the swap is a single-line edit. The `qwen-graphiti` alias is always-loaded on llama-swap (zero swap latency). |
| GB10 llama-swap rate-limits at 25 concurrent writes | Medium | Medium | `chunk_extraction_concurrency: 4` already in YAML caps fan-out; per [`guardkit:TASK-OPS-9F2A`](../../../guardkit/docs/research/dgx-spark/VALIDATION-OPS-7CB1-9F2A-results.md) this eliminated 429s in production. The seeder already uses `helper.drain()` to serialise; Phase-1 latency-spike measured 78s/write (LLM-bound), so 25 sequential writes ≈ 30 min. Acceptable for a one-off seed. |
| GB10 down for an extended period | Low | High (blocks repair) | YAML fallback to MacBook ollama (currently active). If both unreachable, repair task itself slips by the GB10 outage; Phase 2 day-by-day already accounts for this in its slip-to-Sunday contingency. |
| `OpenAIGenericClient` API surface drifts in graphiti-core minor version bumps | Low | Medium | Pin graphiti-core in `pyproject.toml` to `>=0.29,<0.30`. Smoke test (AC-005) catches regression on next bump. |
| Stale FalkorDB indices from earlier broken seeds | Medium | Low | If `Connection closed by server` returns post-fix, drop the `study_tutor` database via `redis-cli -h whitestocks -p 6379 GRAPH.DELETE study_tutor` and re-seed. |

## Implementation hint (non-binding — re-derive during `/feature-plan`)

Likely subtask shape (3–4 waves, ~5 subtasks):

- **Wave 1 — `GraphitiConnectionConfig.from_yaml` loader + DECISION-DF-001 guard.** Adds the loader; rejects cloud providers at config-load. ~30 min.
- **Wave 2 — `_build_llm_client` + `_build_embedder` mirrors of guardkit's pattern.** Inserted into `get_client()` before `Graphiti(...)` construction. Cross-encoder guard (AC-003). ~60 min.
- **Wave 3 — Live smoke test + CC-13 regex audit verification.** ~45 min.
- **Wave 4 — Re-run seed, capture verification evidence, update `phase-1-validation.md`.** ~30 min plus the seed's ~30 min LLM-bound runtime.
- **Wave 5 — End-to-end MCP demo session, capture turn p50/p95.** ~30–45 min.

Total: ~half a day (4 hours) plus the seed's LLM-bound runtime.

## Cross-references

- `docs/research/ideas/phase-1-validation.md` — the gate that falsified G2/G3/G4/G5/G6/G13 and triggered this task.
- `docs/research/ideas/phase-2-build-plan.md §"Day 1"` — Saturday 2 May morning step 3 (where this task slots in).
- `guardkit/guardkit/knowledge/graphiti_client.py` — canonical client; mirror its `_build_llm_client` + `_build_embedder` patterns.
- `guardkit/docs/research/dgx-spark/README.md` — the all-llama.cpp + llama-swap deployment overview; DECISION-DF-001 source.
- `guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md` — production deployment validation (65 GB VRAM, 41.32 tok/s workhorse, all four models coexisting).
- `guardkit/docs/research/dgx-spark/VALIDATION-OPS-7CB1-9F2A-results.md` — `chunk_extraction_concurrency: 4` provenance (eliminates 429 throttling).
- `guardkit/docs/research/dgx-spark/llama-swap-config.yaml` — model-alias registry (`qwen-graphiti`, `nomic-embed`).
- `guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md` — the cross-repo migration task that listed study-tutor as priority-High (still pending; this task supersedes it for study-tutor).
- `specialist-agent/src/specialist_agent/tools/graphiti_client.py` — companion client (search-side use case; ~460 lines; same `OpenAIGenericClient`/`OpenAIEmbedder` pattern).
- `study-tutor/.guardkit/graphiti.yaml` — the source-of-truth config this task wires `get_client` to load from.
- `docs/research/ideas/graphiti-latency-spike-results.md` — `add_episode` median 78s; informs the seed-runtime estimate.
- `tests/unit/knowledge/test_queries.py:_FakeInner` and `tests/unit/knowledge/test_async_write.py:FakeClient` — the mocks that let the integration drift through Phase 1; AC-005's smoke test is the regression-prevention complement.
- `TASK-PH2-GR-002` (sibling task) — long-term: extract guardkit's `graphiti_client.py` + `falkordb_workaround.py` + embedder preflight into a shared `appmilla-graphiti-core` package consumed by guardkit, study-tutor, specialist-agent, and the rest of the fleet. This repair task is intentionally scoped narrower so it can ship today; the extraction task captures the duplication debt for prioritisation later.
Now creating the sibling task for the shared library extraction.

Write TASK-PH2-GR-002-extract-shared-graphiti-core-lib.md
117 lines
---
id: TASK-PH2-GR-002
title: Extract shared Graphiti core library across study-tutor, guardkit, specialist-agent
task_type: refactor
phase: post-hackathon-or-phase-3
implementation_mode: design-first
complexity: 8
estimated_minutes: 1200
status: backlog
priority: medium
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
dependencies:
- TASK-PH2-GR-001
related:
- guardkit:guardkit/knowledge/graphiti_client.py
- specialist-agent:src/specialist_agent/tools/graphiti_client.py
- guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md
tags:
- graphiti
- shared-library
- cross-repo
- debt-reduction
- discussion-starter
- post-hackathon
---

# Extract shared Graphiti core library

## Status: discussion-starter

This task is **scoped from study-tutor but should be promoted to a guardkit-level task** before execution. It's recorded here so the duplication debt is visible from the study-tutor backlog (since study-tutor will be the third consumer once `TASK-PH2-GR-001` lands), but the actual extraction work should live alongside the canonical implementation in guardkit.

**Defer to post-hackathon (after 18 May 2026 submission)** unless one of the trigger conditions below fires.

## Why this exists

There are now **three independent Graphiti client implementations** across the appmilla fleet, all converging on the same `OpenAIGenericClient` + `OpenAIEmbedder` pattern against llama-swap on GB10:

| Repo | File | Lines | Purpose |
|---|---|---|---|
| `guardkit` | `guardkit/knowledge/graphiti_client.py` | ~2496 | Canonical: full LLM/embedder/dimension-preflight/falkordb-workaround/group-prefixing/seeding/init |
| `specialist-agent` | `src/specialist_agent/tools/graphiti_client.py` | ~460 | Search-side: lazy init, graceful degradation, circuit breaker, safe query methods |
| `study-tutor` | `src/study_tutor/knowledge/graphiti_client.py` | (small) | Phase-1: lifecycle wrapper + healthcheck only; no LLM/embedder wiring (about to be repaired by `TASK-PH2-GR-001`) |

Plus there's a fleet-wide config schema (`.guardkit/graphiti.yaml`) shared across **at least 13 repos** per [`guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md`](../../../guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md) — the schema is fully harmonised but each repo loads it differently (or not at all). The endpoint migration that document calls out (vLLM ports 8000/8001 → llama-swap port 9000) was applied to guardkit during v3 deployment but **still pending across the other 13 repos** as of 2026-04-29 — suggesting a shared library could have made that migration a single PR rather than fourteen.

## Proposed scope

A new package — working name `appmilla-graphiti-core` — extracted from the canonical guardkit implementation, with a dependency-inverted public API:

```
appmilla_graphiti_core/
├── __init__.py
├── config/
│   ├── schema.py            # GraphitiConfig dataclass (the .guardkit/graphiti.yaml shape)
│   └── loader.py            # load_from_yaml + env-var overrides
├── client/
│   ├── client.py            # GraphitiClient lifecycle wrapper (initialize / close / healthcheck)
│   ├── llm_factory.py       # _build_llm_client (vllm / ollama / gemini-on-explicit-opt-in)
│   └── embedder_factory.py  # _build_embedder (vllm / ollama)
├── partition/
│   ├── reader.py            # read_partition(driver, group_ids, limit) → (nodes, edges)
│   ├── writer.py            # GraphitiWriteHelper (fire-and-forget add_episode wrapper)
│   └── group_id.py          # GroupIdValidator + namespace prefix constants
├── falkordb_workaround.py   # PR #1170 monkey-patch (single-group_id search bug)
├── preflight.py             # embedding dimension pre-flight check
└── safety/
    ├── decision_df_001.py   # DECISION-DF-001 guard: raise on cloud providers when local-only required
    └── circuit_breaker.py   # specialist-agent's safe-query pattern
```

Three target consumers:

- **guardkit** — replaces `guardkit/knowledge/graphiti_client.py` (the canonical source) with `from appmilla_graphiti_core import GraphitiClient`. The bulk of the existing module's logic lives in the shared lib; the thin remainder is guardkit-specific seeding helpers.
- **study-tutor** — replaces `src/study_tutor/knowledge/graphiti_client.py` and `src/study_tutor/knowledge/async_write.py` (or at least the LLM/embedder construction half) with the shared lib. Keeps the study-tutor-specific `EpisodeBase` / `SessionCompletedEpisode` / `MisconceptionObservedEpisode` types in-repo (they're domain entities, not infra).
- **specialist-agent** — replaces `src/specialist_agent/tools/graphiti_client.py` with the shared lib's `client.py` + `safety/circuit_breaker.py`. The search-side `search_nodes_safe` / `search_facts_safe` methods become library methods.

Plus a long tail (10+ repos per the endpoint-migration task) that don't yet have a Python Graphiti client but consume `.guardkit/graphiti.yaml` indirectly via guardkit's tooling — those become library consumers if/when they ever need direct programmatic Graphiti access.

## Why post-hackathon, not now

- **Submission deadline is Monday 18 May.** The hackathon submission is the load-bearing milestone. Refactoring three repos onto a new shared library is exactly the kind of "while we're here" work that consumes the wrong calendar week.
- **Premature consolidation risk.** The three implementations converge on the same pattern but each has local context (study-tutor's CC-13 single-call-site invariant; specialist-agent's circuit breaker; guardkit's seeding helpers). Forcing them into a shared shape before all three are settled would lock in the wrong abstraction. `TASK-PH2-GR-001` settles study-tutor; that's the third converging point — *then* the shared shape is visible.
- **Test surface multiplies.** Each repo has its own test suite for its Graphiti integration (study-tutor: `tests/unit/knowledge/test_*.py`; guardkit: `tests/knowledge/test_graphiti_*.py`; specialist-agent: `tests/.../test_graphiti_*.py`). A shared lib means a shared test harness — designing that well is its own ~half-day task on top of the extraction.

## Trigger conditions to reopen earlier

Promote to in-progress (and likely to a guardkit-level task) if any of:

- **A second cross-repo Graphiti API drift surfaces** like the one this Phase 1 close-out exercise just exposed. If wiring up another repo to the same llama-swap endpoint requires re-deriving the same `_build_llm_client` / `_build_embedder` pattern from scratch, the case for shared code stops being theoretical.
- **graphiti-core 0.30 ships with a breaking API change.** Pinning each repo's compat code separately gets expensive; centralising means one PR fixes the fleet.
- **A new repo (jarvis, forge, or one of the named-but-not-yet-built fleet members) needs a runtime Graphiti integration before submission.** Building it from scratch when guardkit and study-tutor and specialist-agent already have one each would be a fourth instance of the same code.
- **The `.guardkit/graphiti.yaml` endpoint-migration task ([`guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md`](../../../guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md)) gets reopened to apply the next round of fleet-wide config changes** (e.g. when llama-swap moves off `:9000` or when a new model alias replaces `qwen-graphiti`). The shared-lib path makes that a one-PR change instead of a 13-PR sweep.

## Acceptance criteria (sketch — reshape during `/feature-spec`)

1. **AC-001** — Package published as `appmilla-graphiti-core` (location TBD: pip-installable from a private repo, monorepo subpackage, or a single-source git submodule — the choice depends on the broader appmilla packaging story).
2. **AC-002** — guardkit, study-tutor, and specialist-agent all import the shared client; their individual `graphiti_client.py` modules become thin shims (or are deleted entirely if no repo-specific logic remains).
3. **AC-003** — All three consumers' existing test suites stay green. Shared-lib tests cover: config loader, LLM/embedder factories, DECISION-DF-001 guard, partition read/write, group-id validation, falkordb_workaround, embedding dimension preflight, circuit breaker.
4. **AC-004** — A single-document migration runbook (in guardkit's `docs/research/`) explains how to onboard a new fleet repo to the shared lib in <30 min.
5. **AC-005** — Cross-repo divergence note captured: which group-id namespaces each consumer uses (study-tutor: `student-`/`subject-`/`fleet-appmilla`; guardkit: `product_knowledge`/`command_workflows`/`architecture_decisions`; specialist-agent: TBD). The lib doesn't enforce a single namespace — it provides validators and the consumer chooses the prefixes.

## Out of scope

- **Changing graphiti-core's own surface.** This task wraps graphiti-core; it doesn't fork it.
- **Changing the FalkorDB topology** (Synology NAS via Tailscale). That's a fleet-infrastructure decision, separate task if revisited.
- **Migrating the cross-repo `.guardkit/graphiti.yaml` files to a new shared schema.** They're already on the same schema. The lib just standardises the *loader* that consumes them.

## Cross-references

- `tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md` — the immediate-unblocker task this is the long-term follow-up to.
- `guardkit/guardkit/knowledge/graphiti_client.py` — canonical implementation; the source of truth for the extraction.
- `specialist-agent/src/specialist_agent/tools/graphiti_client.py` — companion search-side implementation; contributes the `_safe` pattern + circuit-breaker.
- `guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md` — the fleet-wide config-migration evidence: 13 repos with the same schema, same migration done piecemeal. The strongest argument for centralisation.
- `guardkit/docs/research/dgx-spark/README.md` — the all-llama.cpp deployment story this lib targets.
Now updating phase-2-build-plan.md references so they reflect the local-only constraint and the new GR-002 follow-up.

Edit phase-2-build-plan.md
Added 1 line
Edit phase-2-build-plan.md
Added 4 lines
Now committing the task updates.

Bash Status before commit
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor status --short

OUT
 M docs/research/ideas/phase-2-build-plan.md
 M tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
?? tasks/backlog/TASK-PH2-GR-002-extract-shared-graphiti-core-lib.md
Bash Commit task updates
IN
git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor add \
  tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md \
  tasks/backlog/TASK-PH2-GR-002-extract-shared-graphiti-core-lib.md \
  docs/research/ideas/phase-2-build-plan.md && git -C /Users/richardwoollcott/Projects/appmilla_github/study-tutor commit -m "$(cat <<'EOF'
docs(phase-2): pivot TASK-PH2-GR-001 to local-only LLM/embedder via llama-swap

Per DECISION-DF-001 (no cloud API on dark factory critical path,
triggered by £30/3-day Gemini spend), the Graphiti runtime integration
repair must use the local GB10 inference fleet, not Gemini. Pivots the
task from "wire Gemini + GB10 embedder + cross-encoder" to "wire local
LLM + embedder via llama-swap on GB10:9000 mirroring guardkit's
canonical OpenAIGenericClient/OpenAIEmbedder pattern".

Key changes to TASK-PH2-GR-001:
- Hard constraints section names DECISION-DF-001 explicitly; cloud
  providers (openai, gemini) raise ValueError at config-load time.
- Anchors the wiring on guardkit/guardkit/knowledge/graphiti_client.py's
  _build_llm_client / _build_embedder methods (the canonical 2496-line
  implementation already used in production with the same llama-swap
  endpoint).
- Config-loading switches from hand-constructed GraphitiConnectionConfig
  to a new from_yaml loader against the existing .guardkit/graphiti.yaml
  (canonical schema shared across the 13-repo fleet per
  guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md).
- Cross-encoder explicitly NOT wired to OpenAI default — added an
  init-time guard so any reranker call at runtime fails loud.
- Removed the [knowledge-graph] pyproject extra plan: OpenAIGenericClient
  + OpenAIEmbedder ship with base graphiti-core, no new pip extras
  needed for local-only operation.
- Complexity reduced 6→5 (mirroring an existing solved pattern is
  simpler than building cloud-API wiring from scratch).
- Cross-references expanded to include the dgx-spark research docs
  (README, v3-production-deployment results, OPS-7CB1/9F2A validation
  for chunk_extraction_concurrency=4, llama-swap-config.yaml model
  aliases).

Adds TASK-PH2-GR-002: extract shared Graphiti core library across
study-tutor + guardkit + specialist-agent. Three repos converge on the
same OpenAIGenericClient/OpenAIEmbedder pattern; the .guardkit/graphiti.yaml
schema is already harmonised across 13+ repos. Discussion-starter, scoped
post-hackathon (after 18 May 2026), with explicit trigger conditions to
reopen earlier (graphiti-core 0.30 breaking change, fourth repo needing
runtime Graphiti, fleet-wide config migration). The task captures the
duplication debt without committing the calendar week to the refactor.

Phase-2-build-plan.md updates:
- Feature Summary table: TASK-PH2-GR-001 description rewritten;
  TASK-PH2-GR-002 row added.
- Saturday Day-1 morning step 3: /feature-spec invocation rewritten
  with the local-only framing, the explicit guardkit context references,
  and the DECISION-DF-001 guard requirement.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

OUT
[main 5949dc0] docs(phase-2): pivot TASK-PH2-GR-001 to local-only LLM/embedder via llama-swap
 3 files changed, 257 insertions(+), 34 deletions(-)
 create mode 100644 tasks/backlog/TASK-PH2-GR-002-extract-shared-graphiti-core-lib.md
Update Todos

Investigate guardkit's graphiti_client.py + config + embedder/LLM wiring

Check study-tutor's existing .guardkit/graphiti.yaml config

Check specialist-agent's Graphiti integration shape

Rewrite TASK-PH2-GR-001 to require local-only (llama-swap) and reuse guardkit patterns

Create TASK-PH2-GR-002: extract shared Graphiti core lib

Update phase-2-build-plan.md to reference new local-only framing + GR-002

Commit task updates
Done. Four commits ahead of origin/main now:
a210472 fix(graphiti): align integration with graphiti-core 0.29 surface
78d3498 docs(phase-1): seed phase-1-validation.md; lead Phase 2 with TASK-PH2-GR-001
732672c docs(phase-2): amend Day 1 plan to lead with TASK-PH2-GR-001
5949dc0 docs(phase-2): pivot TASK-PH2-GR-001 to local-only LLM/embedder via llama-swap
What I found in GuardKit (and how it reshaped GR-001)
The canonical 2496-line client at guardkit/guardkit/knowledge/graphiti_client.py already solves exactly the wiring problem we hit:

_build_llm_client() → OpenAIGenericClient against llama-swap, api_key="local-key" placeholder
_build_embedder() → OpenAIEmbedder against llama-swap, same placeholder
Both ship with base graphiti-core (no new pip extras needed)
cross_encoder left as graphiti-core default (not invoked by add_episode)
And the fleet is bigger than I realised:

The .guardkit/graphiti.yaml schema is already harmonised across 13 repos per guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md. study-tutor was on that migration list as priority-High.
specialist-agent has its own ~460-line Graphiti client (search-side: lazy init, circuit breaker, safe-query methods).
All three converge on the same OpenAIGenericClient/OpenAIEmbedder + llama-swap pattern.
What changed in TASK-PH2-GR-001
Pivot from "Gemini + cloud cross-encoder" → local-only via llama-swap (Qwen2.5-14B FP8 LLM + nomic-embed embeddings, both on GB10:9000).
Added a Hard constraints section naming DECISION-DF-001 (the £30/3-day Gemini-spend incident) — llm_provider in ("openai","gemini") raises ValueError at config-load.
Anchored the wiring on guardkit's _build_llm_client + _build_embedder patterns (mirror, don't reinvent).
Switched config-loading from hand-constructed GraphitiConnectionConfig to a new from_yaml(".guardkit/graphiti.yaml") loader (smallest blast radius; YAML is the cross-repo source of truth).
Cross-encoder explicitly NOT wired to OpenAI default — guard logs a warning at init, treats any runtime reranker call as a critical error.
Dropped the [knowledge-graph] pyproject extra plan (not needed for local-only).
Complexity reduced 6 → 5.
What's new: TASK-PH2-GR-002 (discussion-starter, post-hackathon)
A separate task captures the duplication debt between guardkit / study-tutor / specialist-agent. Proposes extracting the canonical client into a shared appmilla-graphiti-core package. Explicit trigger conditions to reopen earlier:

Second cross-repo Graphiti API drift surfaces
graphiti-core 0.30 breaking change
A fourth fleet repo needs runtime Graphiti before submission
The 13-repo .guardkit/graphiti.yaml migration gets reopened
Otherwise, defer to post-submission (after 18 May 2026) to avoid premature consolidation. The task lives in the study-tutor backlog as visibility but flags itself as "should be promoted to a guardkit-level task before execution."

Phase 2 Day 1 morning sequence is now sharper
The amended /feature-spec invocation in phase-2-build-plan.md:197 passes the guardkit canonical client + dgx-spark research docs as context, so when you run it, the spec generator has the right reference material in hand.

Want me to kick off /feature-spec for TASK-PH2-GR-001 next, or do /system-arch first?

which would you recommend? /system-arch seems the more natural next step to me?
Agreed — /system-arch first. Three reasons:

It's the build plan's documented order (validation gate → system-arch → system-design → system-plan → feature-spec for the immediate task). Following that order keeps the architecture refresh informed by the validation findings rather than retrofitted afterwards.
It's pure doc work that doesn't depend on the runtime being live. GR-001 is the runtime repair; architecture refresh runs cleanly without it.
Its output informs FEAT-PH2-001's spec downstream. The new gamification subsystem (one entity, one relationship, one write-helper method, one event-stream sink) wants to be sketched in ARCHITECTURE.md before /feature-spec for FEAT-PH2-001 runs — and the system-arch output will likely also surface a couple of small refinements to GR-001's scope (e.g., should the from_yaml loader live in knowledge/ or be promoted to a config/ module if Phase 2 adds gamification config too).
The one thing worth flagging: /system-arch should ingest phase-1-validation.md as context so the architecture doc captures the falsification cluster + the local-only DECISION-DF-001 constraint as load-bearing facts going forward. The build plan already lists it (phase-2-build-plan.md:171-178) but worth double-checking before you fire it.

After /system-arch lands (and /system-design + /system-plan if you're chaining all three), the natural next step is /feature-spec + /feature-plan for GR-001, then autobuild it while you start FEAT-PH2-001's spec.

Want me to draft the exact /system-arch invocation including the validation doc as context, or are you good to fire it from here?

please provide the full /feature-spec command syntax with the appropriate --context arguments and I'll use it in a fresh conversation
Bash Verify all proposed --context paths exist
IN
ls -1 \
  tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md \
  docs/research/ideas/phase-1-validation.md \
  docs/research/ideas/phase-2-build-plan.md \
  src/study_tutor/knowledge/graphiti_client.py \
  src/study_tutor/knowledge/queries.py \
  src/study_tutor/knowledge/async_write.py \
  src/study_tutor/knowledge/student_model.py \
  src/study_tutor/knowledge/episodes.py \
  scripts/seed_student_model.py \
  .guardkit/graphiti.yaml \
  ../guardkit/guardkit/knowledge/graphiti_client.py \
  ../guardkit/docs/research/dgx-spark/README.md \
  ../guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md \
  ../guardkit/docs/research/dgx-spark/llama-swap-config.yaml \
  ../guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md \
  ../specialist-agent/src/specialist_agent/tools/graphiti_client.py 2>&1

OUT
../guardkit/docs/research/dgx-spark/llama-swap-config.yaml
../guardkit/docs/research/dgx-spark/README.md
../guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md
../guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md
../guardkit/guardkit/knowledge/graphiti_client.py
../specialist-agent/src/specialist_agent/tools/graphiti_client.py
.guardkit/graphiti.yaml
docs/research/ideas/phase-1-validation.md
docs/research/ideas/phase-2-build-plan.md
scripts/seed_student_model.py
src/study_tutor/knowledge/async_write.py
src/study_tutor/knowledge/episodes.py
src/study_tutor/knowledge/graphiti_client.py
src/study_tutor/knowledge/queries.py
src/study_tutor/knowledge/student_model.py
tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
All 16 candidate paths exist. Here's the full command, organised so you can drop it straight in:


/feature-spec "Graphiti runtime integration repair — wire local LLM + embedder via llama-swap on GB10:9000 (no cloud APIs per DECISION-DF-001); load config from .guardkit/graphiti.yaml; mirror guardkit's canonical OpenAIGenericClient/OpenAIEmbedder pattern; re-seed Lilymay; run end-to-end MCP demo" \
  --context tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md \
  --context docs/research/ideas/phase-1-validation.md \
  --context src/study_tutor/knowledge/graphiti_client.py \
  --context src/study_tutor/knowledge/queries.py \
  --context src/study_tutor/knowledge/async_write.py \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/knowledge/episodes.py \
  --context scripts/seed_student_model.py \
  --context tests/unit/knowledge/test_async_write.py \
  --context .guardkit/graphiti.yaml \
  --context ../guardkit/guardkit/knowledge/graphiti_client.py \
  --context ../guardkit/docs/research/dgx-spark/README.md \
  --context ../guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md \
  --context ../guardkit/docs/research/dgx-spark/llama-swap-config.yaml
Run from the study-tutor working directory (/Users/richardwoollcott/Projects/appmilla_github/study-tutor) — the ../guardkit/... cross-repo paths are relative to it.

What each context contributes
#	Path	Why it's there
1	tasks/backlog/TASK-PH2-GR-001-...md	The 8 ACs the spec must cover
2	docs/research/ideas/phase-1-validation.md	The falsification cluster + DECISION-DF-001 framing the task exists to repair
3	src/study_tutor/knowledge/graphiti_client.py	The file with the wiring gap — what the spec is repairing
4	src/study_tutor/knowledge/queries.py	Read-side seam (already-patched in a210472) — informs AC-001/004 scope boundary
5	src/study_tutor/knowledge/async_write.py	Write-side seam (already-patched) — same
6	src/study_tutor/knowledge/student_model.py	STUDENT_GROUP_PREFIX etc. for the smoke-test/seed scenarios (AC-005, AC-006)
7	src/study_tutor/knowledge/episodes.py	EpisodeBase / SessionCompletedEpisode types — needed for AC-005 smoke-test scenario shape
8	scripts/seed_student_model.py	The AC-006 consumer — defines what "seed lands" means in concrete terms
9	tests/unit/knowledge/test_async_write.py	Existing mock pattern (FakeClient) — informs how the new live smoke test diverges from the unit-test surface
10	.guardkit/graphiti.yaml	Source-of-truth config schema for the AC-004 from_yaml loader
11	../guardkit/.../graphiti_client.py	The canonical 2496-line implementation to mirror (_build_llm_client, _build_embedder)
12	../guardkit/.../dgx-spark/README.md	DECISION-DF-001 source + the all-llama.cpp / llama-swap stack overview
13	../guardkit/.../dgx-spark/RESULTS-v3-production-deployment.md	Production validation evidence — informs AC-001/002 (the wiring is known-good in production)
14	../guardkit/.../dgx-spark/llama-swap-config.yaml	Model alias registry (qwen-graphiti, nomic-embed) — names the spec scenarios should reference
Optional adds (drop them in if /feature-spec asks for more depth)
docs/research/ideas/phase-2-build-plan.md — the orchestrating plan; useful if scenario timing matters.
../specialist-agent/src/specialist_agent/tools/graphiti_client.py — companion 460-line client with the safe-query / circuit-breaker pattern; relevant only if AC-003's reranker-guard scenarios need richer "graceful degradation" language.
../guardkit/docs/research/dgx-spark/VALIDATION-OPS-7CB1-9F2A-results.md — chunk_extraction_concurrency: 4 provenance; relevant if scenarios need to reference the rate-limit risk.
../guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md — fleet-wide migration evidence; relevant only if scenarios need to call out cross-repo config consistency.
tests/unit/knowledge/test_queries.py — only if the spec wants scenarios about the read-side mock-vs-live divergence.
Quick sanity check before you fire it in the fresh conversation
The fresh conversation won't have any of our build-plan amendments / phase-1-validation reasoning loaded in working memory. The --context paths above include phase-1-validation.md and the task file, which together carry that whole story. So the new conversation will start cold but with the full audit trail.

If /feature-spec's clarification phase asks anything that would benefit from our session's reasoning, the answer is almost always findable in phase-1-validation.md (the falsification cluster + root cause) or the task file (the 8 ACs + DECISION-DF-001 hard constraint).

do you have enough context wimndow left to run /feature-spec?
Honest answer: probably not safely.

This session is already heavily loaded — multiple file reads (including a deep dive into guardkit's 2496-line graphiti_client.py), three patch rounds with full test runs, two seed-run tracebacks, the phase-1-validation.md write, two task files, four commits, and the build-plan amendments. /feature-spec is itself heavy: it'll re-load all 14 --context files (the guardkit canonical client alone is substantial), run the propose-review loop iteratively, generate 30+ BDD scenarios across smoke/key-example/boundary/negative/edge-case categories, then run the AC-quality linter and bdd-linker. Risk of running out mid-task is real.

The fresh-conversation approach is also genuinely cleaner regardless of context budget:

The task file + phase-1-validation.md already carry the full audit trail. Nothing about my in-session reasoning is uniquely valuable that isn't captured in those docs.
A clean conversation gives /feature-spec a focused workspace optimised for that one deliverable.
If /feature-spec's clarification phase asks something tricky, the new conversation can answer cleanly from the --context files rather than half-remembering my session.
Stick with the original plan: fire the command in a fresh conversation. The command I gave you in the previous message is self-contained.