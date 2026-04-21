# TASK-PO02-006 Parity Log

**Date:** 2026-04-20
**Task:** TASK-PO02-006 — Parity surface verification and unit tests
**Feature:** FEAT-PO-002 (Tutoring runtime — MCP adapter + LLM client)
**Dependencies verified:** TASK-PO02-001 through TASK-PO02-005 (all completed)

Formal acceptance gate for the six structural-requirement parity surfaces
(SR-01, SR-02, SR-03, SR-04, SR-05, SR-06, SR-07). SR-01 and SR-03 are
covered by executable tests; SR-02/SR-04/SR-06/SR-07 are shell-verified
below with the exact commands and captured output; SR-05 is a documented
Phase-0 pass-through.

---

## SR-01 — stdio discipline (code-tested)

**Locus:** `src/study_tutor/cli/main.py`, FastMCP transport.
**Contract:** stdout is reserved for MCP JSON-RPC; banners and logs go to stderr.

**Test file:** `tests/unit/mcp/test_stdio_discipline.py`
**Command:**
```
.venv/bin/pytest tests/unit/mcp/test_stdio_discipline.py -v
```

**Output:**
```
tests/unit/mcp/test_stdio_discipline.py::test_serve_writes_zero_bytes_to_stdout_during_idle_startup PASSED
tests/unit/mcp/test_stdio_discipline.py::test_serve_emits_banner_on_stderr PASSED
================== 2 passed in 3.14s ==================
```

Both tests spawn the real `study-tutor serve --role tutor --transport stdio`
subprocess with stdin closed (`subprocess.DEVNULL`) and assert:
1. Zero bytes on stdout during the 3-second startup window.
2. The `[study-tutor]` banner and `MCP server '...' ready` log line land on stderr.

Implementation already shipped correctly by TASK-PO02-005 / TASK-PO02-002
(cli wires `logging.basicConfig(stream=sys.stderr, ...)` and
`click.echo(..., err=True)`). No drift fixed.

**Status:** ✅ GREEN

---

## SR-02 — CWD absolute path (shell-verified)

**Locus:** `scripts/mcp-wrapper.sh`.
**Contract:** wrapper `cd`s to an absolute repo root — no `$PWD`, no relative paths.

**Commands and output:**
```
$ grep -nE '^REPO_ROOT="/' scripts/mcp-wrapper.sh
14:REPO_ROOT="/Users/richardwoollcott/Projects/appmilla_github/study-tutor"

$ grep -nE 'PWD' scripts/mcp-wrapper.sh
(no match)

$ grep -nE '^\s*cd ' scripts/mcp-wrapper.sh
16:cd "$REPO_ROOT"
```

**Note on grep pattern:** the acceptance-criterion grep `^cd /` was written
assuming an inline `cd /absolute/path`. The shipped wrapper uses the
idiomatic variable-indirection pattern (`REPO_ROOT="/…"; cd "$REPO_ROOT"`),
which is still an absolute path — just parameterised at the top of the file
so operators can edit it in one place. The two checks above
(`^REPO_ROOT="/` + no `$PWD`) verify the same SR-02 invariant and are
therefore used instead. The wrapper's inline comment on line 13 explicitly
documents "absolute path, not $PWD".

**README coverage:** `README.md` `MCP wrapper` section documents SR-02.

**Status:** ✅ GREEN (no drift fixed)

---

## SR-03 — provider resolution (code-tested)

**Locus:** `src/study_tutor/llm/client.py::_default_player_model`,
`src/study_tutor/mcp/adapter.py` (every handler).
**Contract:** providers resolved at call time via `_default_player_model()`;
no module-level `LLMClient()` instance; no provider string literals inside
handler bodies.

**Test file:** `tests/unit/llm/test_provider_resolution.py`
**Command:**
```
.venv/bin/pytest tests/unit/llm/test_provider_resolution.py -v
```

**Output:**
```
test_agent_models_reasoning_model_format                      PASSED
test_bedrock_provider_raises_not_implemented                  PASSED
test_unsupported_provider_raises_llm_provider_error           PASSED
test_local_provider_posts_to_ollama_with_system_prompt        PASSED
test_local_provider_omits_system_when_none                    PASSED
test_local_provider_wraps_http_errors                         PASSED
test_no_module_level_client_instantiation                     PASSED
test_adapter_handlers_do_not_reference_provider_string_literals PASSED
================== 8 passed in 0.52s ==================
```

Key assertions aligned with the TASK-PO02-006 acceptance criteria:
- `_default_player_model()` returns `"local"` when env is unset and
  `"bedrock"` when env is set to `"bedrock"` —
  `test_agent_models_reasoning_model_format`.
- `LLMClient(provider="bedrock").generate(...)` raises `NotImplementedError`
  matching `"FEAT-PO-004"` — `test_bedrock_provider_raises_not_implemented`.
- Grep assertion: adapter source contains no provider-string literals
  (`local`, `bedrock`, `openai`, `anthropic`, `gemini`) in executable code
  (docstrings and comments stripped first) —
  `test_adapter_handlers_do_not_reference_provider_string_literals` (added
  by this task).

**Status:** ✅ GREEN (one test added to close the adapter-grep gap)

---

## SR-04 — providers extras completeness (shell-verified)

**Locus:** `pyproject.toml` `[project.optional-dependencies].providers`.
**Contract:** every provider listed is actually installed in the venv.

**Command and output:**
```
$ for pkg in langchain-openai langchain-anthropic langchain-google-genai \
             langchain-aws langchain-ollama; do
    .venv/bin/pip show "$pkg" > /dev/null && echo "  ✓ $pkg" || echo "  ✗ $pkg"
  done
  ✓ langchain-openai
  ✓ langchain-anthropic
  ✓ langchain-google-genai
  ✓ langchain-aws
  ✓ langchain-ollama
```

**Status:** ✅ GREEN (no drift fixed)

---

## SR-05 — Dockerfile parity (pass-through)

**Locus:** N/A for Phase 0 — no Dockerfile shipped.

Per the task description and `docs/research/ideas/phase-0-scope.md`, SR-05
is a structural pass-through in Phase 0. When Phase 1 re-activates container
builds, this surface must be re-verified at that point (forward-reference:
**Phase 1 Dockerfile re-activation**).

**Status:** ✅ GREEN (intentional pass-through)

---

## SR-06 — .env hygiene (shell-verified)

**Locus:** `.env.example`, `.gitignore`.
**Contract:** no secret-shaped placeholders; all placeholders are
`<angle-bracket>` form; `.env` is gitignored.

**Commands and output:**
```
$ grep -nE '=(sk-[a-zA-Z0-9]+|AIza[a-zA-Z0-9]+|not_needed|sk-test)' .env.example
(no match — ✓)

$ grep -nE '^[A-Z_]+=[^<]' .env.example
10:AGENT_MODELS__REASONING_MODEL=local
```

The one non-`<…>` value (`AGENT_MODELS__REASONING_MODEL=local`) is the
intended **default enum value**, not a placeholder — it documents that
Phase 0 runs on the local Ollama provider out of the box. All credential
and URL placeholders (Ollama host/model, AWS region, Bedrock ARN, API keys)
use `<angle-bracket>` form.

```
$ grep -nE '^\.env$' .gitignore
139:.env

$ git check-ignore -v .env
.gitignore:139:.env	.env
```

`.env` is correctly ignored; a populated `.env` will not appear in
`git status`.

**Status:** ✅ GREEN (no drift fixed)

---

## SR-07 — tool description ≡ behaviour (shell-verified)

**Locus:** `src/study_tutor/mcp/server.py` (registration descriptions) +
`src/study_tutor/mcp/adapter.py` (handler bodies).
**Contract:** each MCP tool's user-facing description matches the behaviour
of the handler it names.

**Descriptions as shipped** (from `grep -nE 'description=' src/study_tutor/mcp/server.py`):

| Tool | Description | Handler behaviour | Match |
|---|---|---|---|
| `tutor_start_session` | "Long-running, returns session_id immediately; LLM model is warmed up in the background." | `adapter.tutor_start_session` creates a `SessionStore` row, returns `{"session_id"}`, and fires `asyncio.create_task(self._warm_up(...))`. Returns in ≪1 s. | ✓ |
| `tutor_turn` | "Sync, typically returns within 15s." | `adapter.tutor_turn` awaits `asyncio.to_thread(client.generate, ...)` synchronously and returns `{"tutor_response"}`. No background work. | ✓ |
| `tutor_session_status` | "Sync, returns current session state." | `adapter.tutor_session_status` is a pure read — looks up the session from the store and returns its fields. Literal match. | ✓ |
| `tutor_session_end` | "Marks session ended." | `adapter.tutor_session_end` flips status via `self._store.end(session_id)`. The Phase-1 Graphiti write lives as a `# TODO(phase-1)` comment — **not** in the description. Literal match. | ✓ |

Also verified by the existing `tests/unit/mcp/test_adapter.py::test_server_registers_four_tools`, which
asserts `"graphiti" not in description.lower()` and `"async" not in description.lower()`
for `tutor_session_end`.

**Status:** ✅ GREEN (no drift fixed)

---

## Full-suite regression

```
$ .venv/bin/pytest tests/
============================= 21 passed in 6.27s ==============================
```

No existing test was modified. Three tests added in total:
- `tests/unit/llm/test_provider_resolution.py::test_adapter_handlers_do_not_reference_provider_string_literals` (closes the SR-03 adapter-grep gap)
- `tests/unit/mcp/test_stdio_discipline.py::test_serve_writes_zero_bytes_to_stdout_during_idle_startup` (new file — SR-01)
- `tests/unit/mcp/test_stdio_discipline.py::test_serve_emits_banner_on_stderr` (same file — SR-01)

---

## Six parity surfaces: GREEN
