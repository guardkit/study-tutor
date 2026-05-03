richardwoollcott@Richards-MBP study-tutor % GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-FD32 --verbose
INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-FD32 (max_turns=5, stop_on_failure=True, resume=False, fresh=False, refresh=False, sdk_timeout=None, enable_pre_loop=None, timeout_multiplier=None, max_parallel=None, max_parallel_strategy=static, bootstrap_failure_mode=None)
INFO:guardkit.orchestrator.feature_orchestrator:Raised file descriptor limit: 256 → 4096
INFO:guardkit.orchestrator.feature_orchestrator:FeatureOrchestrator initialized: repo=/Users/richardwoollcott/Projects/appmilla_github/study-tutor, max_turns=5, stop_on_failure=True, resume=False, fresh=False, refresh=False, enable_pre_loop=None, enable_context=True, task_timeout=3000s
INFO:guardkit.orchestrator.feature_orchestrator:Starting feature orchestration for FEAT-FD32
INFO:guardkit.orchestrator.feature_orchestrator:Phase 1 (Setup): Loading feature FEAT-FD32
╭───────────────────────────────────────────────────────────────────── GuardKit AutoBuild ─────────────────────────────────────────────────────────────────────╮
│ AutoBuild Feature Orchestration                                                                                                                              │
│                                                                                                                                                              │
│ Feature: FEAT-FD32                                                                                                                                           │
│ Max Turns: 5                                                                                                                                                 │
│ Stop on Failure: True                                                                                                                                        │
│ Mode: Starting                                                                                                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.feature_loader:Loading feature from /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/features/FEAT-FD32.yaml
✓ Loaded feature: Graphiti Runtime Integration Repair
  Tasks: 5
  Waves: 5
✓ Feature validation passed
✓ Pre-flight validation passed
INFO:guardkit.cli.display:WaveProgressDisplay initialized: waves=5, verbose=True
✓ Created shared worktree: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-GR-LOAD-yaml-loader-and-decision-df-001-guard.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-GR-WIRE-build-llm-client-and-embedder-with-cross-encoder-sentinel.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-GR-SMOK-graphiti-runtime-smoke-test.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-GR-DEMO-end-to-end-mcp-tutor-session.md
✓ Copied 5 task file(s) to worktree
⚙ Bootstrapping environment: python
INFO:guardkit.orchestrator.feature_orchestrator:Bootstrap failure-mode smart default = 'block' (manifests declaring requires-python: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32/pyproject.toml)
INFO:guardkit.orchestrator.environment_bootstrap:Running install for python (pyproject.toml): uv pip sync uv.lock
WARNING:guardkit.orchestrator.environment_bootstrap:Install failed for python (pyproject.toml) with exit code 2:
stderr: error: Couldn't parse requirement in `uv.lock` at position 0
  Caused by: no such comparison operator "=", must be one of ~= == != <= >= < > ===
version = 1
        ^^^

stdout: (empty)
⚠ Environment bootstrap partial: 0/1 succeeded
ERROR:guardkit.orchestrator.feature_orchestrator:Feature orchestration failed: Bootstrap hard-fail: 0/1 install(s) succeeded for essential stack(s): python.
Manifest: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32/pyproject.toml
Manifest requires-python: >=3.11
Install stderr (tail):
error: Couldn't parse requirement in `uv.lock` at position 0
  Caused by: no such comparison operator "=", must be one of ~= == != <= >= < > ===
version = 1
        ^^^
Hint: set `bootstrap_failure_mode: warn` in .guardkit/config.yaml (or pass `--bootstrap-failure-mode warn`) to downgrade this to a non-blocking warning.
Traceback (most recent call last):
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py", line 728, in orchestrate
    feature, worktree = self._setup_phase(feature_id, base_branch)
                        ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py", line 947, in _setup_phase
    return self._create_new_worktree(feature, feature_id, base_branch)
           ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py", line 987, in _create_new_worktree
    self._bootstrap_environment(worktree)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py", line 1291, in _bootstrap_environment
    self._maybe_hardfail_bootstrap(result)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py", line 1416, in _maybe_hardfail_bootstrap
    raise FeatureOrchestrationError(
        _format_bootstrap_hardfail_message(result, essential_stacks)
    )
guardkit.orchestrator.feature_orchestrator.FeatureOrchestrationError: Bootstrap hard-fail: 0/1 install(s) succeeded for essential stack(s): python.
Manifest: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32/pyproject.toml
Manifest requires-python: >=3.11
Install stderr (tail):
error: Couldn't parse requirement in `uv.lock` at position 0
  Caused by: no such comparison operator "=", must be one of ~= == != <= >= < > ===
version = 1
        ^^^
Hint: set `bootstrap_failure_mode: warn` in .guardkit/config.yaml (or pass `--bootstrap-failure-mode warn`) to downgrade this to a non-blocking warning.
Orchestration error: Failed to orchestrate feature FEAT-FD32: Bootstrap hard-fail: 0/1 install(s) succeeded for essential stack(s): python.
Manifest: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32/pyproject.toml
Manifest requires-python: >=3.11
Install stderr (tail):
error: Couldn't parse requirement in `uv.lock` at position 0
  Caused by: no such comparison operator "=", must be one of ~= == != <= >= < > ===
version = 1
        ^^^
Hint: set `bootstrap_failure_mode: warn` in .guardkit/config.yaml (or pass `--bootstrap-failure-mode warn`) to downgrade this to a non-blocking warning.
ERROR:guardkit.cli.autobuild:Feature orchestration error: Failed to orchestrate feature FEAT-FD32: Bootstrap hard-fail: 0/1 install(s) succeeded for essential stack(s): python.
Manifest: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32/pyproject.toml
Manifest requires-python: >=3.11
Install stderr (tail):
error: Couldn't parse requirement in `uv.lock` at position 0
  Caused by: no such comparison operator "=", must be one of ~= == != <= >= < > ===
version = 1
        ^^^
Hint: set `bootstrap_failure_mode: warn` in .guardkit/config.yaml (or pass `--bootstrap-failure-mode warn`) to downgrade this to a non-blocking warning.
richardwoollcott@Richards-MBP study-tutor %