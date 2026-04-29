richardwoollcott@Richards-MBP study-tutor % GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-1773 --verbose
INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-1773 (max_turns=5, stop_on_failure=True, resume=False, fresh=False, refresh=False, sdk_timeout=None, enable_pre_loop=None, timeout_multiplier=None, max_parallel=None, max_parallel_strategy=static, bootstrap_failure_mode=None)
INFO:guardkit.orchestrator.feature_orchestrator:Raised file descriptor limit: 256 → 4096
INFO:guardkit.orchestrator.feature_orchestrator:FeatureOrchestrator initialized: repo=/Users/richardwoollcott/Projects/appmilla_github/study-tutor, max_turns=5, stop_on_failure=True, resume=False, fresh=False, refresh=False, enable_pre_loop=None, enable_context=True, task_timeout=3000s
INFO:guardkit.orchestrator.feature_orchestrator:Starting feature orchestration for FEAT-1773
INFO:guardkit.orchestrator.feature_orchestrator:Phase 1 (Setup): Loading feature FEAT-1773
╭───────────────────────────── GuardKit AutoBuild ─────────────────────────────╮
│ AutoBuild Feature Orchestration                                              │
│                                                                              │
│ Feature: FEAT-1773                                                           │
│ Max Turns: 5                                                                 │
│ Stop on Failure: True                                                        │
│ Mode: Starting                                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.feature_loader:Loading feature from /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/features/FEAT-1773.yaml
ERROR:guardkit.orchestrator.feature_orchestrator:Feature orchestration failed: Invalid smoke_gates configuration:
6 validation errors for SmokeGates
after_wave
  Field required [type=missing, input_value={'after_wave_1': ['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
command
  Field required [type=missing, input_value={'after_wave_1': ['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
after_wave_1
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t...sodeBase.model_fields"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_2
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t... $count" && exit 1)\''}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_3
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t...d_session_completion)"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_4
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "import scrip...ire_client_or_exit\')"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
Traceback (most recent call last):
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_loader.py", line 645, in _parse_feature
    smoke_gates = SmokeGates.model_validate(smoke_gates_data)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/pydantic/main.py", line 716, in model_validate
    return cls.__pydantic_validator__.validate_python(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        obj,
        ^^^^
    ...<5 lines>...
        by_name=by_name,
        ^^^^^^^^^^^^^^^^
    )
    ^
pydantic_core._pydantic_core.ValidationError: 6 validation errors for SmokeGates
after_wave
  Field required [type=missing, input_value={'after_wave_1': ['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
command
  Field required [type=missing, input_value={'after_wave_1': ['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
after_wave_1
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t...sodeBase.model_fields"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_2
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t... $count" && exit 1)\''}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_3
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t...d_session_completion)"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_4
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "import scrip...ire_client_or_exit\')"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py", line 709, in orchestrate
    feature, worktree = self._setup_phase(feature_id, base_branch)
                        ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py", line 792, in _setup_phase
    feature = FeatureLoader.load_feature(
        feature_id,
        repo_root=self.repo_root,
        features_dir=self.features_dir,
    )
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_loader.py", line 551, in load_feature
    feature = FeatureLoader._parse_feature(data)
  File "/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_loader.py", line 647, in _parse_feature
    raise SchemaValidationError(
        f"Invalid smoke_gates configuration:\n{e}"
    ) from e
guardkit.orchestrator.feature_loader.SchemaValidationError: Invalid smoke_gates configuration:
6 validation errors for SmokeGates
after_wave
  Field required [type=missing, input_value={'after_wave_1': ['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
command
  Field required [type=missing, input_value={'after_wave_1': ['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
after_wave_1
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t...sodeBase.model_fields"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_2
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t... $count" && exit 1)\''}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_3
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t...d_session_completion)"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_4
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "import scrip...ire_client_or_exit\')"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
Orchestration error: Failed to orchestrate feature FEAT-1773: Invalid
smoke_gates configuration:
6 validation errors for SmokeGates
after_wave
  Field required [type=missing, input_value={'after_wave_1':
['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
command
  Field required [type=missing, input_value={'after_wave_1':
['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
after_wave_1
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c
"from study_t...sodeBase.model_fields"'], input_type=list]
    For further information visit
https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_2
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c
"from study_t... $count" && exit 1)\''}], input_type=list]
    For further information visit
https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_3
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c
"from study_t...d_session_completion)"'], input_type=list]
    For further information visit
https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_4
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c
"import scrip...ire_client_or_exit\')"'], input_type=list]
    For further information visit
https://errors.pydantic.dev/2.12/v/extra_forbidden
ERROR:guardkit.cli.autobuild:Feature orchestration error: Failed to orchestrate feature FEAT-1773: Invalid smoke_gates configuration:
6 validation errors for SmokeGates
after_wave
  Field required [type=missing, input_value={'after_wave_1': ['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
command
  Field required [type=missing, input_value={'after_wave_1': ['python...re_client_or_exit\')"']}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
after_wave_1
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t...sodeBase.model_fields"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_2
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t... $count" && exit 1)\''}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_3
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "from study_t...d_session_completion)"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
after_wave_4
  Extra inputs are not permitted [type=extra_forbidden, input_value=['python -c "import scrip...ire_client_or_exit\')"'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
richardwoollcott@Richards-MBP study-tutor %