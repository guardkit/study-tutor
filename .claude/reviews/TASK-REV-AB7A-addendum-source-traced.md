# Diagnostic Addendum — Source-Traced Validation with C4 Sequence Diagrams

**Companion to:** [.claude/reviews/TASK-REV-AB7A-report.md](./TASK-REV-AB7A-report.md)
**Generated:** 2026-04-30 (revision after [R]evise)
**Trigger:** User asked whether the suggested fixes target this repo or guardkit, and asked for execution-flow tracing across system/technological boundaries with C4 sequence diagrams to validate findings before resume.

GuardKit is **editable-installed** at `/home/richardwoollcott/Projects/appmilla_github/guardkit` (verified via `direct_url.json: {"editable": true}`). Source quoted in this addendum is the *active* code path that ran during the failed FEAT-70A4 autobuild.

---

## 0. Scope Clarification — Where Each Fix Lands

| Fix | Layer | Files Touched | Runs in |
|---|---|---|---|
| **FIX-AB7A-001** Pin smoke-gate interpreter | THIS repo | [.guardkit/features/FEAT-70A4.yaml](../../.guardkit/features/FEAT-70A4.yaml) | study-tutor only |
| **FIX-AB7A-002** Backfill PRV-002 seam test | THIS repo | new `tests/unit/knowledge/test_seam_corpus_loader.py` | study-tutor only |
| **FIX-AB7A-003** Backfill PRV-003 seam test | THIS repo | new `tests/unit/knowledge/test_seam_retrieval_decision.py` | study-tutor only |
| **FIX-AB7A-004** Serialise waves 3+ | THIS repo | [.guardkit/features/FEAT-70A4.yaml](../../.guardkit/features/FEAT-70A4.yaml) | study-tutor only |
| **FIX-AB7A-005** Resume autobuild | THIS repo | run command | study-tutor only |
| GK-UPSTREAM-1 Smoke-gate venv resolution | **guardkit repo** | `guardkit/orchestrator/smoke_gates.py` | all features |
| GK-UPSTREAM-2 Tighten conditional-approval | **guardkit repo** | `guardkit/orchestrator/quality_gates/coach_validator.py` | all features |
| GK-UPSTREAM-3 Source-overlap detection in planner | **guardkit repo** | `/feature-plan` | all features |
| GK-UPSTREAM-4 Block on missing seam tests | **guardkit repo** | `coach_validator.py` | all features |
| GK-UPSTREAM-5 SDK reader transport | **upstream Claude SDK** | external | all features |

**All five FIX-AB7A-* tasks land in this repo. None require guardkit changes.** The guardkit-side findings are filed as a separate upstream backlog and do not block resume.

---

## 1. System Context (C4 L1) — Where the Boundaries Are

```mermaid
graph TB
    User[Operator<br/>shell on Linux 24] -->|"guardkit autobuild feature FEAT-70A4"| CLI[guardkit CLI<br/>~/.agentecflow/bin/guardkit]
    CLI -->|"dispatch"| Orchestrator[FeatureOrchestrator<br/>shared worktree per feature]
    Orchestrator -->|"asyncio.to_thread per task"| AutoBuild[AutoBuildOrchestrator<br/>per task, same worktree]
    AutoBuild -->|"Player phase"| SDK[Claude Agent SDK<br/>subprocess transport]
    AutoBuild -->|"Coach phase"| CoachVal[CoachValidator<br/>independent test verifier]
    Orchestrator -->|"after each wave"| SmokeGate[smoke_gates.run_smoke_gate<br/>shell=True subprocess]
    Orchestrator -->|"phase 0"| Bootstrap[EnvironmentBootstrapper<br/>creates .guardkit/venv]

    Bootstrap -.->|"writes"| Worktree[(Shared Worktree<br/>.guardkit/worktrees/FEAT-70A4<br/>branch: autobuild/FEAT-70A4)]
    AutoBuild -.->|"reads + writes + commits"| Worktree
    CoachVal -.->|"reads"| Worktree
    SmokeGate -.->|"reads + executes from"| Worktree
    Worktree -.->|"installed editable"| Venv[(.guardkit/venv<br/>study-tutor 0.1.0 editable)]

    SDK -.->|"5x fatal errors,<br/>fallback to subprocess"| AutoBuild
    CoachVal -.->|"build_venv_env<br/>looks at .venv/bin only"| Venv
    SmokeGate -.->|"❌ no env injection<br/>shells bare 'python'"| HostPath[(System PATH<br/>only python3, no python)]

    classDef bug fill:#fdd,stroke:#c00,stroke-width:2px
    classDef contention fill:#fec,stroke:#c80,stroke-width:2px
    class SmokeGate,HostPath bug
    class Worktree contention
```

**Key boundary insight:** Every component that touches the worktree is *aware* of the bootstrap venv except `smoke_gates.run_smoke_gate`. The shared worktree is also a parallel-write hazard the orchestrator does not currently fence.

---

## 2. C4 L4 Sequence — Bootstrap → Smoke Gate (proves Root Cause #1)

This sequence proves the smoke gate has **no path** to the bootstrap interpreter. Sources are quoted verbatim.

```mermaid
sequenceDiagram
    autonumber
    participant CLI as guardkit CLI<br/>cli/autobuild.py
    participant FO as FeatureOrchestrator<br/>feature_orchestrator.py
    participant EB as EnvironmentBootstrapper<br/>environment_bootstrap.py
    participant Shell as bash subprocess<br/>shell=True
    participant Venv as .guardkit/venv/bin/python<br/>(editable study-tutor)
    participant Sys as /usr/bin/python3<br/>(system, no 'python')

    CLI->>FO: orchestrate(feature_id="FEAT-70A4")
    FO->>EB: bootstrap_environment(worktree)
    EB->>Sys: /usr/bin/python3 -m pip install -e .
    Sys-->>EB: PEP 668 externally-managed (FAIL)
    EB->>EB: create venv at <worktree>/.guardkit/venv
    EB->>Venv: <venv>/bin/python -m pip install -e .
    Venv-->>EB: success (editable install)
    EB-->>FO: BootstrapResult(venv_python=<venv>/bin/python)
    Note over FO: feature_orchestrator.py:1297-1306<br/>self._bootstrap_venv_python = result.venv_python<br/>logs: "Coach pytest interpreter set..."
    FO->>FO: _execute_wave_parallel(wave=2)
    Note over FO: AutoBuildOrchestrator receives _bootstrap_venv_python<br/>(line 644 comment)
    FO->>FO: smoke_gate after wave 2 fires
    FO->>Shell: subprocess.run(config.command, shell=True, cwd=worktree)
    Note over Shell: smoke_gates.py:163<br/>❌ NO env= argument<br/>❌ NO interpreter parameter in run_smoke_gate signature
    Shell->>Sys: /bin/bash -c 'set -e; python -c "..." ; pytest ...'
    Sys-->>Shell: bash: line 2: python: command not found
    Shell-->>FO: returncode=127
    FO->>FO: SmokeGateResult(passed=False, exit_code=127)
    Note over FO: Halt; preserve worktree
```

**Verbatim source proof:**

```python
# guardkit/orchestrator/smoke_gates.py:124-170
def run_smoke_gate(
    config: SmokeGates,
    cwd: Path,
    wave_number: int,            # ← only 3 params; no interpreter, no env
) -> SmokeGateResult:
    ...
    proc = subprocess.run(
        config.command,
        shell=True,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=config.timeout,  # ← NO env=...
    )
```

Compare with `coach_validator.py:2415-2453` which DOES inject venv PATH:

```python
# guardkit/orchestrator/quality_gates/coach_validator.py:2415-2453
env = build_venv_env(self.worktree_path)
if env is not None:
    logger.info("Prepended virtualenv PATH: %s", self.worktree_path / ".venv" / "bin")
proc = subprocess.run(
    cmd,
    shell=True,
    cwd=str(self.worktree_path),
    ...,
    env=env,                     # ← env injected
)
```

And `command_models.py:79-96` (the helper):

```python
# guardkit/orchestrator/quality_gates/command_models.py:79-96
def build_venv_env(worktree_path):
    """If the worktree contains a .venv/bin directory, returns an
    env with PATH prepended..."""
    venv_bin = worktree_path / ".venv" / "bin"   # ← only checks .venv/bin
    if venv_bin.is_dir():
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
```

**Two compounding upstream defects:**
- (a) `smoke_gates.run_smoke_gate` doesn't pass `env=` at all.
- (b) Even if it did and called `build_venv_env`, the helper only inspects `.venv/bin`, while the bootstrap creates `.guardkit/venv/bin` (per `environment_bootstrap.py:1078`). So the helper would have returned `None` here.

**Why this proves the local fix is safe:** the bootstrap reliably puts the venv at `<worktree>/.guardkit/venv/bin/python` (verified on disk for this run). Pinning that path *literally* in the YAML works regardless of upstream defects (a) or (b).

---

## 3. C4 L4 Sequence — Wave-2 Parallel Execution (proves Root Cause #2)

This sequence proves the parallel-contention failure is **structural source-file contention** — not the type the existing TASK-ABFIX-005 isolation was designed to handle.

```mermaid
sequenceDiagram
    autonumber
    participant FO as FeatureOrchestrator
    participant T2 as Task PRV-002 thread<br/>AutoBuildOrchestrator
    participant T3 as Task PRV-003 thread<br/>AutoBuildOrchestrator
    participant WT as Shared Worktree<br/>branch: autobuild/FEAT-70A4
    participant BDD as features/.../test_primary_text_rag_and_quote_verifier.py<br/>(SHARED 888-line glue)
    participant CV2 as Coach for PRV-002
    participant CV3 as Coach for PRV-003

    FO->>T2: asyncio.to_thread(run, PRV-002)
    FO->>T3: asyncio.to_thread(run, PRV-003)
    par Parallel Player phase
        T2->>BDD: write step defs for @task:TASK-PRV-002
        T2->>WT: git commit -m "[guardkit-checkpoint] Turn 1"
    and
        T3->>BDD: write step defs for @task:TASK-PRV-003
        T3->>WT: git commit -m "[guardkit-checkpoint] Turn 1"
    end
    Note over WT: Both commits land on same branch.<br/>BDD file now contains a merge of both edits<br/>OR one's edits overwrote the other's.
    par Parallel Coach phase
        T2->>CV2: validate(PRV-002)
        CV2->>CV2: run_isolated_tests(wave_size=2)
        Note over CV2: coach_validator.py:1701<br/>tempfile.TemporaryDirectory<br/>shutil.copytree(worktree, tmp)
        CV2->>BDD: snapshot BDD file (already inconsistent!)
        CV2->>CV2: pytest in tmp → undefined steps for one task
        CV2->>CV2: _classify_test_failure → parallel_contention<br/>(wave_size>1, output looks contention-like)
        CV2->>CV2: conditional_approval rule fires<br/>line 865: parallel_contention + all_gates_passed → True
        CV2-->>T2: APPROVED (independent tests skipped)
    and
        T3->>CV3: validate(PRV-003) → same path, same outcome
        CV3-->>T3: APPROVED (independent tests skipped)
    end
    FO->>FO: wave 2 complete; smoke gate fires (then 127s)
```

**Why TASK-ABFIX-005 isolation does not help:**

The isolation logic (`coach_validator.py:1700-1750`) snapshots the worktree to a tempdir to defend against *concurrent mutation during test execution*. It cannot defend against **already-inconsistent committed state** at the moment the snapshot is taken. Both PRV-002 and PRV-003 had committed conflicting edits to the shared BDD glue file *before* either verification phase started.

**Verbatim source proof of the rule misfiring:**

```python
# guardkit/orchestrator/quality_gates/coach_validator.py:851-874
conditional_approval = (
    failure_class == "infrastructure"
    and failure_confidence == "high"
    and bool(requires_infra)            # ← requires_infra ≠ []
    and not docker_available
    and gates_status.all_gates_passed
) or (
    failure_class == "collection_error"
    and gates_status.all_gates_passed
) or (
    # TASK-ABFIX-005: Grant conditional approval for contention-related
    # failures in a parallel wave when all Player quality gates passed.
    failure_class == "parallel_contention"
    and gates_status.all_gates_passed   # ← THIS branch fired for FEAT-70A4
) or (
    failure_class == "code"
    and self.is_parallel
    and gates_status.all_gates_passed
) or environment_conditional_approval
```

The `parallel_contention` branch (line 865) does **not** check `requires_infra` — by design, the rule was deliberately broadened in TASK-ABFIX-005 to cover all parallel-wave failures. That decision is sound for cases where contention is transient (race conditions on shared services); it is unsound for cases where two parallel tasks have committed conflicting writes to the same source file. There is no way for `_classify_test_failure` to distinguish these two cases from test output alone — they look identical.

**Why the local fix is durable:** serialising waves 3 and 4 in `FEAT-70A4.yaml` ensures only one task can write to the shared BDD glue at a time. We don't depend on the rule getting tightened upstream.

---

## 4. C4 Component View — Coach Approval Decision Tree

```mermaid
graph TD
    Start[Independent test verification result] --> AllPass{all tests passed?}
    AllPass -->|yes| ApprovedClean[APPROVED clean]
    AllPass -->|no| Classify[_classify_test_failure]
    Classify --> FC{failure_class}

    FC -->|infrastructure + high| InfraPath{requires_infra<br/>declared AND<br/>Docker unavailable?}
    InfraPath -->|yes| CondApprovedInfra[CONDITIONAL approve<br/>infrastructure path]
    InfraPath -->|no| FeedbackPath[FEEDBACK to Player]

    FC -->|collection_error| AllGates1{all_gates_passed?}
    AllGates1 -->|yes| CondApprovedColl[CONDITIONAL approve<br/>collection_error path]

    FC -->|parallel_contention| AllGates2{all_gates_passed?}
    AllGates2 -->|yes| CondApprovedPC[CONDITIONAL approve<br/>parallel_contention path<br/>⚠ FIRED FOR FEAT-70A4]

    FC -->|code| IsParallel{is_parallel AND<br/>all_gates_passed?}
    IsParallel -->|yes| CondApprovedCode[CONDITIONAL approve<br/>code-in-parallel path]

    FC -->|infrastructure + ambiguous<br/>+ bootstrap_likely_broken| EnvPath{not requires_infra<br/>AND all_gates_passed?}
    EnvPath -->|yes| CondApprovedEnv[CONDITIONAL approve<br/>environment path]

    classDef fired fill:#fec,stroke:#c80,stroke-width:3px
    classDef ok fill:#dfd,stroke:#080
    classDef bad fill:#fdd,stroke:#c00
    class CondApprovedPC fired
    class ApprovedClean ok
    class FeedbackPath bad
```

The `parallel_contention` path (right side) **does not check `requires_infra`** — that's the upstream policy gap. Local serialisation (FIX-AB7A-004) sidesteps the entire decision tree by ensuring only one task per wave can fail this way.

---

## 5. C4 L4 Sequence — Resume Path with Local Fixes (proves no regression)

```mermaid
sequenceDiagram
    autonumber
    participant Op as Operator
    participant CLI as guardkit CLI
    participant FO as FeatureOrchestrator<br/>(--resume)
    participant EB as EnvironmentBootstrapper
    participant SG as smoke_gates<br/>(unchanged code)
    participant T4 as PRV-004 (alone)
    participant T5 as PRV-005 (alone)
    participant T6 as PRV-006 (alone)
    participant T7 as PRV-007 (alone)
    participant Venv as <wt>/.guardkit/venv/bin/python

    Note over Op,Venv: Pre-resume manual verification (in this repo)
    Op->>Venv: .guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import ..."
    Venv-->>Op: exit 0
    Op->>Op: run new seam tests<br/>.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_*.py
    Op->>Op: edit FEAT-70A4.yaml smoke_gates.command<br/>edit orchestration.parallel_groups (serialise waves 3+)
    Op->>CLI: guardkit autobuild feature FEAT-70A4 --resume
    CLI->>FO: orchestrate(resume=True)
    FO->>FO: detect existing worktree at .guardkit/worktrees/FEAT-70A4
    FO->>EB: bootstrap_environment (idempotent)
    EB-->>FO: BootstrapResult(venv_python=<wt>/.guardkit/venv/bin/python)
    FO->>FO: load wave plan: waves 3,4,5 now serial
    FO->>T4: run PRV-004 (only task in wave 3)
    T4-->>FO: approved (no parallel contention possible)
    FO->>SG: smoke_gate after wave 3
    SG->>Venv: <wt>/.guardkit/venv/bin/python -c "..."
    Venv-->>SG: exit 0
    SG->>Venv: <wt>/.guardkit/venv/bin/python -m pytest tests/unit/knowledge/ -x -q
    Venv-->>SG: exit 0
    SG-->>FO: SmokeGateResult(passed=True)
    FO->>T5: run PRV-005 (only task in wave 4)
    T5-->>FO: approved
    FO->>SG: smoke_gate after wave 4 (passes via venv path)
    FO->>T6: run PRV-006 (only task in wave 5)
    T6-->>FO: approved
    FO->>T7: run PRV-007 (only task in wave 6)
    T7-->>FO: approved
    FO->>FO: feature complete; merge worktree to main
```

**Why this provably does not regress autobuild:**

| Risk | Mitigation | Evidence |
|---|---|---|
| Other features' smoke gates break | Change is local to `FEAT-70A4.yaml`. Other feature YAMLs untouched. | YAML is feature-scoped. |
| Bootstrap path could vary | Bootstrap reliably writes to `<worktree>/.guardkit/venv/bin/python` (single hardcoded path in `environment_bootstrap.py:1078`). | `venv_python = venv_dir / "bin" / "python"`. |
| Smoke gate `cwd` could vary | `cwd` is *always* the worktree path (`smoke_gates.py:140-141` docstring + transcript line 817). Relative path `.guardkit/venv/bin/python` resolves correctly. | Code + transcript. |
| Serialisation breaks parallelism elsewhere | Change is local to `FEAT-70A4.yaml.orchestration.parallel_groups`. Default planner behaviour for other features is unaffected. | YAML scope. |
| `--resume` reuses stale state | `_setup_phase` re-bootstraps the venv (idempotent), and the worktree is on a known commit (`5e2ecdf`). | feature_orchestrator.py:892-913. |
| Seam tests reveal latent PRV-002/003 bug | Run them locally *before* `--resume`; if they fail, escalate to a code-fix subtask before resume. | This is the gate condition in §6 below. |

**No upstream guardkit changes are made by any of the FIX-AB7A-* tasks.** Other features' autobuild behaviour is byte-for-byte unchanged.

---

## 6. Pre-Resume Gate Conditions (mandatory before FIX-AB7A-005)

The resume command must NOT run until these checks pass locally in this repo:

```bash
cd /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4

# 1. venv interpreter still resolves the editable install
.guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import \
  CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
# expected: exit 0

# 2. existing knowledge unit tests still pass
.guardkit/venv/bin/python -m pytest tests/unit/knowledge/ -x -q
# expected: exit 0 (this would have been the smoke gate result if the gate had used the venv path)

# 3. NEW: PRV-002 seam test passes (proves loader-models contract)
.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_corpus_loader.py -v
# expected: exit 0
# if FAILS: do NOT resume; escalate to code-fix subtask for PRV-002

# 4. NEW: PRV-003 seam test passes (proves decision-function contract)
.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_retrieval_decision.py -v
# expected: exit 0
# if FAILS: do NOT resume; escalate to code-fix subtask for PRV-003

# 5. updated smoke gate command runs cleanly
/bin/bash -c 'set -e
.guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import \
  CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
.guardkit/venv/bin/python -m pytest tests/unit/knowledge/ -x -q'
# expected: exit 0
```

Only when all five pass: `guardkit autobuild feature FEAT-70A4 --resume`.

---

## 7. Revised Recommendations (Validated)

The original recommendations stand, but with three refinements informed by source reading:

1. **FIX-AB7A-001 (smoke-gate pin) is now expressed as a literal-path edit, not a venv activation.** Source confirms `cwd` is the worktree, so a relative path `.guardkit/venv/bin/python` will resolve correctly. Activation (`source .guardkit/venv/bin/activate`) is unnecessary and would add a fragile shell-quoting concern under `shell=True`.

2. **FIX-AB7A-004 (wave serialisation) targets waves 3 only — wave 4 is already a single task** (PRV-006 alone per the original plan), and wave 5 is already a single task (PRV-007 alone). Re-reading `FEAT-70A4.yaml:127-135`, wave 3 is `[PRV-004, PRV-005]` — that's the only multi-task wave that remains. Splitting it suffices. (Wave 2 already executed; no change needed.)

3. **FIX-AB7A-002/003 (seam tests) are now load-bearing gate conditions, not optional**. If either fails, do NOT resume — fix the underlying code first. Source-tracing shows the conditional-approval rule provides no other safety net against this class of failure.

---

## 8. Upstream Filings (Out of Scope, but Documented)

These should be filed against the guardkit repo. They are NOT part of the FIX-AB7A-* fix feature.

- **GK-UPSTREAM-1** [smoke_gates: honour bootstrap interpreter] `guardkit/orchestrator/smoke_gates.py:124-170` — `run_smoke_gate` should accept `venv_python: Optional[str]` and PATH-prepend `<venv_python>.parent` (or pass `env=build_venv_env(cwd)`). Two-line change in `run_smoke_gate` plus one-line change in the caller in `feature_orchestrator.py`. Also: `command_models.build_venv_env` should consult `.guardkit/venv/bin` in addition to `.venv/bin`.
- **GK-UPSTREAM-2** [conditional_approval: distinguish source-file contention] `coach_validator.py:851-874` — the `parallel_contention` branch should check whether the failing test command touches paths edited by other in-flight tasks in this wave. If yes, do not auto-approve; require a serialised retry instead.
- **GK-UPSTREAM-3** [planner: warn on wave-internal source overlap] `/feature-plan` should detect when multiple tasks in the same `parallel_groups` entry edit the same `features/<slug>/test_*.py` glue or other shared sources and emit a planner warning suggesting serialisation or per-task BDD glue files.
- **GK-UPSTREAM-4** [coach: block on planned-but-unimplemented seam tests] when a task file's `## Seam Tests` section is non-empty but no `@pytest.mark.seam` test was collected from the worktree, Coach should fail the gate (not warn).
- **GK-UPSTREAM-5** [SDK reader transport] `Fatal error in message reader: Command failed with exit code 1` fires once per Coach SDK pytest gate; subprocess fallback always recovers. File against guardkit + Claude Agent SDK for transport-layer investigation.

The first four are small, targeted changes (1–10 lines each in the files identified). They can be filed as separate guardkit issues with this report's evidence section attached.

---

## 9. Updated Decision

The diagnosis is now source-traced and the regression risk for the local fix path is *zero*. Recommendation remains **[I]mplement** the FIX-AB7A-* feature, with the pre-resume gate conditions in §6 as mandatory checks before FIX-AB7A-005.

If you want me to also draft the GitHub issue text for the five GK-UPSTREAM-* filings (so they can be opened against the guardkit repo separately), say so when choosing [I]mplement and I'll bundle them.
