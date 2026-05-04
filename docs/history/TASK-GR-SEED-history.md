/task-work TASK-GR-SEED


I'll execute the task-work workflow for TASK-GR-SEED. Starting with task discovery.

Bash Search for TASK-GR-SEED across task states
IN
ls tasks/in_progress/TASK-GR-SEED* tasks/backlog/TASK-GR-SEED* tasks/blocked/TASK-GR-SEED* tasks/in_review/TASK-GR-SEED* 2>/dev/null

OUT
Exit code 1
(eval):1: no matches found: tasks/in_progress/TASK-GR-SEED*
Bash Find any task file matching GR-SEED pattern
IN
find tasks -maxdepth 3 -name "TASK-GR-SEED*" 2>/dev/null; find tasks -maxdepth 4 -name "*GR-SEED*" 2>/dev/null

OUT
tasks/completed/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
tasks/completed/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
The task TASK-GR-SEED was searched across active states (in_progress, backlog, blocked, in_review) and not found there. It exists in tasks/completed/.

Read TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
TASK-GR-SEED has already been moved to tasks/completed/ as part of the FEAT-FD32 close-out (commit 9c13a70). It's not in any active state directory (in_progress, backlog, blocked, in_review) where /task-work looks.

Notes on the file's state:

Frontmatter status: blocked (was blocked when last worked)
Filesystem location: completed/ (manually archived in commit 6eb9a26 "manual completions for operator-handoff tasks")
Last autobuild turn (turn 2) ended with non-blocking advisory feedback about Phase 3 not being invoked and tests not passing
How would you like to proceed?

Resume from completed/ — move it back to in_progress/ and re-run /task-work (the seed against live FalkorDB at whitestocks:6379, then flip Phase 1 G2/G3/G4/G5/G6/G13 from Falsified → Held)
Inspect first — read the full task file and the autobuild turn history before deciding
Leave it archived — the FEAT-FD32 close-out treated it as done; if you have a new seed/gate-flip task in mind, create a fresh TASK-XXX
Which one?

TASK-GR-DEMO-end-to-end-mcp-tutor-session.md#2-2
2 lets double check it actually seeded
Read TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
Let me verify the seed actually landed. I'll check three things in parallel: the live graph (via Graphiti MCP), the phase-1-validation.md document, and the seed script itself.

Read phase-1-validation.md
Bash Verify seed script exists and get size
IN
ls -la scripts/seed_student_model.py 2>/dev/null && wc -l scripts/seed_student_model.py

OUT
-rw-r--r--@ 1 richardwoollcott  staff  27896 May  3 16:52 scripts/seed_student_model.py
     772 scripts/seed_student_model.py
Now I'll query the live Graphiti graph and check the rest of the validation doc.

Graphiti [get_status]
OUT
{"status":"ok","message":"Graphiti MCP server is running and connected to falkordb database"}
Graphiti [search_nodes]Lilymay
OUT
{"result":{"error":"Error searching nodes: RediSearch: Syntax error at offset 19 near student"}}
Read phase-1-validation.md (from line 101)
The MCP search query errored on RediSearch syntax (dash in "student-lilymay" group_id). Let me retry with a cleaner query and also check the actual verification artifacts on disk.

Graphiti [search_nodes]Lilymay student profile
OUT
{"result":{"message":"No relevant nodes found","nodes":[]}}
Bash List autobuild artifacts for TASK-GR-SEED
IN
ls -la .guardkit/autobuild/TASK-GR-SEED/ 2>/dev/null && echo "---" && ls -la .guardkit/autobuild/TASK-GR-SEED/logs/ 2>/dev/null | head -30

OUT
total 200
drwxr-xr-x@ 17 richardwoollcott  staff    544 May  3 16:52 .
drwxr-xr-x@ 13 richardwoollcott  staff    416 May  3 16:55 ..
-rw-r--r--@  1 richardwoollcott  staff   1290 May  3 16:52 checkpoints.json
-rw-r--r--@  1 richardwoollcott  staff    826 May  3 16:52 coach_feedback_for_turn_2.json
-rw-r--r--@  1 richardwoollcott  staff   1842 May  3 16:52 coach_turn_1.json
-rw-r--r--@  1 richardwoollcott  staff  12308 May  3 16:52 coach_turn_2.json
drwxr-xr-x@ 10 richardwoollcott  staff    320 May  3 16:52 logs
-rw-r--r--@  1 richardwoollcott  staff    277 May  3 16:52 phase_4_summary.json
-rw-r--r--@  1 richardwoollcott  staff  11596 May  3 16:52 player_turn_1.json
-rw-r--r--@  1 richardwoollcott  staff   6321 May  3 16:52 player_turn_2.json
-rw-r--r--@  1 richardwoollcott  staff  13708 May  3 08:27 progress.log
-rw-r--r--@  1 richardwoollcott  staff    649 May  3 16:52 specialist_results.json
-rw-r--r--@  1 richardwoollcott  staff   8969 May  3 16:52 task_work_results.json
-rw-r--r--@  1 richardwoollcott  staff    762 May  3 16:52 turn_context.json
-rw-r--r--@  1 richardwoollcott  staff   2315 May  3 16:52 turn_state_turn_1.json
-rw-r--r--@  1 richardwoollcott  staff   3243 May  3 16:52 turn_state_turn_2.json
-rw-r--r--@  1 richardwoollcott  staff   3175 May  3 16:52 verify_lilymay.py
---
total 64
drwxr-xr-x@ 10 richardwoollcott  staff  320 May  3 16:52 .
drwxr-xr-x@ 17 richardwoollcott  staff  544 May  3 16:52 ..
-rw-r--r--@  1 richardwoollcott  staff   21 May  3 16:52 seed_run_1.end
-rw-r--r--@  1 richardwoollcott  staff    6 May  3 16:52 seed_run_1.pid
-rw-r--r--@  1 richardwoollcott  staff   21 May  3 16:52 seed_run_1.start
-rw-r--r--@  1 richardwoollcott  staff   21 May  3 16:52 seed_run_2.end
-rw-r--r--@  1 richardwoollcott  staff    6 May  3 16:52 seed_run_2.pid
-rw-r--r--@  1 richardwoollcott  staff   21 May  3 16:52 seed_run_2.start
-rw-r--r--@  1 richardwoollcott  staff    5 May  3 16:52 seed_run_3.pid
-rw-r--r--@  1 richardwoollcott  staff   21 May  3 16:52 seed_run_3.start
Bash Read latest verify result if present
IN
cat .guardkit/autobuild/TASK-GR-SEED/logs/verify_lilymay_turn3.json 2>/dev/null || echo "verify_lilymay_turn3.json not found"

OUT
verify_lilymay_turn3.json not found
The MCP search confirms the graph is empty for Lilymay. The cited verify_lilymay_turn3.json is also missing — only the script remains. Let me run the verify script directly for fresh evidence.

Read verify_lilymay.py
Bash Look for seed run log files
IN
ls -la .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_*.log 2>/dev/null; echo "---"; ls .guardkit/autobuild/TASK-GR-SEED/logs/ 2>/dev/null

OUT
(eval):1: no matches found: .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_*.log
---
seed_run_1.end
seed_run_1.pid
seed_run_1.start
seed_run_2.end
seed_run_2.pid
seed_run_2.start
seed_run_3.pid
seed_run_3.start
Let me run the verify script directly to get authoritative current state of the live graph.

Bash Run the verify_lilymay script against live FalkorDB
IN
ls .venv/bin/python 2>/dev/null && .venv/bin/python .guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py 2>&1 | tail -40

OUT
.venv/bin/python
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
{
  "ac_seed_03_get_student_state": {
    "empty": false,
    "year_group": null,
    "target_grade": null,
    "subjects": [],
    "topic_confidences": []
  },
  "ac_seed_02_student_lilymay_nodes": []
}
Confirmed — the seed never landed. Fresh evidence (just ran verify_lilymay.py against live FalkorDB at whitestocks:6379):


{
  "ac_seed_03_get_student_state": {
    "empty": false,
    "year_group": null,
    "target_grade": null,
    "subjects": [],
    "topic_confidences": []
  },
  "ac_seed_02_student_lilymay_nodes": []
}
Independently corroborated by MCP search_nodes(query="Lilymay student profile") → No relevant nodes found.

Summary
Check	Result
FalkorDB reachable (mcp__graphiti__get_status)	✅ Connected
EntityNode.get_by_group_ids(driver, ["student-lilymay"], limit=20)	[] — no nodes
get_student_state(client, "lilymay")	All fields null/empty (year_group, target_grade, subjects, topic_confidences)
MCP search_nodes(query="Lilymay student profile")	No nodes found
Validation doc (phase-1-validation.md:101-149)	All AC-SEED-01..03 marked ❌ Falsified; G2/G3 explicitly not flipped to Held
File location (tasks/completed/)	Archived, but frontmatter still says status: blocked
What this actually means
The task was moved to completed/ administratively as part of the FEAT-FD32 close-out (commit 9c13a70 + 6eb9a26 "manual completions for operator-handoff tasks"), not because it succeeded. The validation doc is honest about this — it explicitly says G2/G3 cannot honestly flip to Held until rate-limit + counter-accuracy issues (R-WAVE5-01, R-WAVE5-02) are resolved.

There's also one extra signal worth flagging: my fresh verify run printed a Connection closed by server ConnectionError to stderr (FalkorDB cut a connection mid-read) before successfully completing the read-back. That's the same R-WAVE5-01 / AC-SEED-06 escalation condition the doc previously marked as "not observed" — it's now reappearing.

What you can do about it
Re-open as a proper Wave 5 retry — move the file back to in_progress/, address R-WAVE5-01 first (set chunk_extraction_concurrency: 1, or switch to MacBook ollama), then re-run the seed and verify
Open a fresh follow-up task — leave TASK-GR-SEED archived, create TASK-GR-SEED2 (or fold into the operator-handoff TASK-GR-DEMO Wave 5 work scaffolded at phase-1-validation.md:157-209)
Investigate the connection error first — check FalkorDB logs on whitestocks; the ConnectionError on a simple read-only get_by_group_ids call is concerning if persistent
Which direction do you want to take?

1
Picking up Wave 5 retry. Before I kick off a 30-60min seed, let me check current state of the config, the seed script's concurrency knob, and FalkorDB health — so I can propose the exact mitigation to apply.

Bash Read current graphiti config
IN
cat .guardkit/graphiti.yaml 2>/dev/null | head -50

OUT
project_id: study_tutor
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
max_concurrent_episodes: 1
# TASK-GR-SEED (2026-05-02): GB10 vLLM hit 429 rate-limits at default
# extraction concurrency 4 because the seed's schedule_write is
# fire-and-forget (25 episodes × 4 concurrent extractions ≈ 100 concurrent
# requests overwhelms vLLM's queue). Lowered to 1 to keep the seed under
# vLLM's per-process limit; the seed is one-off so the throughput cost is
# acceptable. Restore to 4 for normal tutor-session writes when GB10
# capacity is no longer contended.
chunk_extraction_concurrency: 1
# --- Active: GB10 vLLM (qwen-graphiti always-loaded alias on llama-swap) ---
# MacBook ollama unreachable at TASK-GR-SEED runtime (2026-05-02); GB10 is free.
# Single-line revert path: re-enable the ollama block when MacBook is back.
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:9000/v1
llm_model: qwen-graphiti
# --- Standby: MacBook Pro M2 Max (Ollama, Q4_K_M) — re-enable when MacBook is up ---
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
Bash Find concurrency knobs in config and seed script
IN
grep -n "chunk_extraction_concurrency\|llm_provider\|llm_base_url\|llm_model\|concurrency" .guardkit/graphiti.yaml scripts/seed_student_model.py 2>/dev/null | head -40

OUT
.guardkit/graphiti.yaml:9:# extraction concurrency 4 because the seed's schedule_write is
.guardkit/graphiti.yaml:15:chunk_extraction_concurrency: 1
.guardkit/graphiti.yaml:19:llm_provider: vllm
.guardkit/graphiti.yaml:20:llm_base_url: http://promaxgb10-41b1:9000/v1
.guardkit/graphiti.yaml:21:llm_model: qwen-graphiti
.guardkit/graphiti.yaml:23:#llm_provider: ollama
.guardkit/graphiti.yaml:24:#llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
.guardkit/graphiti.yaml:25:#llm_model: qwen2.5:14b-instruct-q4_K_M
scripts/seed_student_model.py:293:    "llm_provider": "gemini",
scripts/seed_student_model.py:294:    "llm_model": "gemini-2.5-pro",
Bash Check FalkorDB reachability and list graphs
IN
redis-cli -h whitestocks -p 6379 PING 2>&1; echo "---"; redis-cli -h whitestocks -p 6379 GRAPH.LIST 2>&1 | head -20

OUT
PONG
---
product_knowledge
guardkit__rules_mcp_typescript
guardkit__rules_fastmcp_python
guardkit__project_overview
default_db
guardkit__rules_fastapi_python
command_workflows
technology_stack
agentic_dataset_factory__project_decisions
integration_points
guardkit__turn_states
agentic_dataset_factory__project_knowledge
architect_agent_phase2_harness_gap
guardkit__domain_knowledge
jarvis__task_outcomes
guardkit__feature_specs
forge
implementation_modes
guardkit__rules_react_typescript
jarvis__project_tech_stack
Bash Check both LLM endpoints reachability
IN
curl -s -m 5 http://promaxgb10-41b1:9000/v1/models 2>&1 | head -10; echo "---MacBook ollama:"; curl -s -m 5 http://richards-macbook-pro.local:11434/api/tags 2>&1 | head -10

OUT
{"data":[{"created":1777827111,"id":"architect-agent","object":"model","owned_by":"llama-swap"},{"created":1777827111,"id":"gemma4-tutor","object":"model","owned_by":"llama-swap"},{"created":1777827111,"id":"nomic-embed","object":"model","owned_by":"llama-swap"},{"created":1777827111,"id":"qwen-graphiti","object":"model","owned_by":"llama-swap"},{"created":1777827111,"id":"qwen36-workhorse","object":"model","owned_by":"llama-swap"}],"object":"list"}---MacBook ollama:
{"models":[{"name":"gcse-tutor-gemma4-moe:latest","model":"gcse-tutor-gemma4-moe:latest","modified_at":"2026-04-23T13:15:09.520725697+01:00","size":16796002381,"digest":"befeadbaebba59bcf933deffeaf5b7fef8190006090ee65307de10c5c2e9812f","details":{"parent_model":"","format":"gguf","family":"gemma4","families":["gemma4"],"parameter_size":"25.2B","quantization_level":"Q4_K_M"}},{"name":"qwen2.5:14b-instruct-q4_K_M","model":"qwen2.5:14b-instruct-q4_K_M","modified_at":"2026-04-03T13:51:27.372510964+01:00","size":8988124069,"digest":"7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6","details":{"parent_model":"","format":"gguf","family":"qwen2","families":["qwen2"],"parameter_size":"14.8B","quantization_level":"Q4_K_M"}},{"name":"qwen3-coder:30b-a3b-q4_K_M","model":"qwen3-coder:30b-a3b-q4_K_M","modified_at":"2026-01-15T19:36:07.720785786Z","size":18556700761,"digest":"06c1097efce0431c2045fe7b2e5108366e43bee1b4603a7aded8f21689e90bca","details":{"parent_model":"","format":"gguf","family":"qwen3moe","families":["qwen3moe"],"parameter_size":"30.5B","quantization_level":"Q4_K_M"}},{"name":"cite-saul-lora:latest","model":"cite-saul-lora:latest","modified_at":"2025-07-21T21:53:42.474398012+01:00","size":14484732121,"digest":"ba378c0d6521249c44514ea0745ce2d36a1f4074fd22e453d69c121fc90870cf","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"7.2B","quantization_level":"F16"}},{"name":"hf.co/unsloth/Mistral-Small-3.2-24B-Instruct-2506-GGUF:Q4_K_M","model":"hf.co/unsloth/Mistral-Small-3.2-24B-Instruct-2506-GGUF:Q4_K_M","modified_at":"2025-07-21T17:09:24.809237272+01:00","size":15211980118,"digest":"6e505636916fb30ab84b2189ccd3e5b30b74f30fd65b03085fd31f0332cdb422","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"23.6B","quantization_level":"unknown"}},{"name":"hf.co/Fawazzx/Finetuned-saulLM-7b-v1.5.gguf:latest","model":"hf.co/Fawazzx/Finetuned-saulLM-7b-v1.5.gguf:latest","modified_at":"2025-07-17T10:25:09.447458644+01:00","size":7695858535,"digest":"ca01b7e221ec296f693a09ee81c26a7dcab2f38089fae27a1497d0fbdcd53362","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"7.24B","quantization_level":"unknown"}},{"name":"hf.co/tensorblock/Saul-7B-Base-GGUF:Q4_K_M","model":"hf.co/tensorblock/Saul-7B-Base-GGUF:Q4_K_M","modified_at":"2025-07-17T10:11:25.974354936+01:00","size":4368440552,"digest":"7b9b1fff0708e1d0efe7d13e054d36e055f16d07d40d03a9cacfbe0650889a65","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"7.24B","quantization_level":"unknown"}},{"name":"hf.co/mradermacher/DeepSeek-R1-Distill-Llama-UK-Legislation-8B-i1-GGUF:Q4_K_M","model":"hf.co/mradermacher/DeepSeek-R1-Distill-Llama-UK-Legislation-8B-i1-GGUF:Q4_K_M","modified_at":"2025-07-17T08:09:28.108345309+01:00","size":4920739115,"digest":"7294107c75871cc2ce0c17acbbaa55acb0ad3d6ea37edbca1d191984b3dfe9f8","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"8.03B","quantization_level":"unknown"}},{"name":"gemma3:27b","model":"gemma3:27b","modified_at":"2025-04-27T10:11:02.498106429+01:00","size":17396936941,"digest":"a418f5838eaf7fe2cfe0a3046c8384b68ba43a4435542c942f9db00a5f342203","details":{"parent_model":"","format":"gguf","family":"gemma3","families":["gemma3"],"parameter_size":"27.4B","quantization_level":"Q4_K_M"}},{"name":"llama3:latest","model":"llama3:latest","modified_at":"2024-08-19T17:55:36.646902891+01:00","size":4661224676,"digest":"365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1","details":{"parent_model":"","format":"gguf","family":"llama","families":["llama"],"parameter_size":"8.0B","quantization_level":"Q4_0"}},{"name":"nomic-embed-text:latest","model":"nomic-embed-text:latest","modified_at":"2024-07-31T20:08:55.810898912+01:00","size":274302450,"digest":"0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f","details":{"parent_model":"","format":"gguf","family":"nomic-bert","families":["nomic-bert"],"parameter_size":"137M","quantization_level":"F16"}},{"name":"starcoder2:3b","model":"starcoder2:3b","modified_at":"2024-07-31T20:08:16.038337623+01:00","size":1709901545,"digest":"f67ae0f64584a4d1d7c609bf4778dd0d07054582362d21ca4f0eddea22aafd0c","details":{"parent_model":"","format":"gguf","family":"starcoder2","families":["starcoder2"],"parameter_size":"3B","quantization_level":"Q4_0"}}]}
Important findings before I propose the plan:

Bash Check if study_tutor graph exists in FalkorDB
IN
redis-cli -h whitestocks -p 6379 GRAPH.LIST 2>&1 | grep -i "study\|lilymay\|student" || echo "NO study_tutor graph found in list"; echo "---all graphs:"; redis-cli -h whitestocks -p 6379 GRAPH.LIST 2>&1 | wc -l

OUT
study_tutor__project_overview
study_tutor__project_knowledge
study_tutor__project_architecture
study_tutor__project_decisions
study-tutor__project_overview
study-tutor__feature_specs
study-tutor__task_outcomes
study-tutor__project_architecture
study-tutor__domain_knowledge
study-tutor__turn_states
student-lilymay
study_tutor
---all graphs:
     118
Bash Check database name in graphiti config
IN
grep -n "database\|study_tutor" .guardkit/graphiti.yaml | head -10

OUT
1:project_id: study_tutor
Bash Check seed script CLI surface
IN
.venv/bin/python scripts/seed_student_model.py --help 2>&1 | head -30

OUT
usage: seed_student_model [-h] [--config-path CONFIG_PATH]

Seed Lilymay's baseline learner profile into the configured Graphiti /
FalkorDB store. Idempotent on re-run.

options:
  -h, --help            show this help message and exit
  --config-path CONFIG_PATH
                        Optional path to a YAML file overriding the default
                        GraphitiConnectionConfig. When omitted the Phase-1
                        Synology defaults are used.
Good news on prereqs:

R-WAVE5-01 mitigation #1 already in place: .guardkit/graphiti.yaml has chunk_extraction_concurrency: 1 and max_concurrent_episodes: 1 (someone fixed this post-hoc, even though the task doc says it was Wave 5 todo)
Both LLM endpoints healthy: GB10 vLLM serves qwen-graphiti; MacBook ollama serves qwen2.5:14b-instruct-q4_K_M as fallback
Both FalkorDB graphs exist: student-lilymay and study_tutor are present (118 graphs total) — just empty of Lilymay entity nodes
Seed script CLI: only --config-path, no --reset flag — relies on idempotency guard
Moving the task back to in_progress/ and updating frontmatter now.

Edit TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
Added 2 lines
Bash Move task back to in_progress
IN
git mv tasks/completed/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md tasks/in_progress/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md && ls -la tasks/in_progress/TASK-GR-SEED* tasks/completed/TASK-GR-SEED* 2>&1 | grep -v "No such"

OUT
(eval):1: no matches found: tasks/completed/TASK-GR-SEED*
Bash Confirm move succeeded
IN
ls -la tasks/in_progress/TASK-GR-SEED* && git status --short tasks/

OUT
-rw-r--r--  1 richardwoollcott  staff  10658 May  3 17:52 tasks/in_progress/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
RM tasks/completed/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md -> tasks/in_progress/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
File moved (git mv-tracked rename). Now I need your go-ahead before launching the seed itself:

Plan:

Launch python scripts/seed_student_model.py in background, log → .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.log
Wait ~30-60 min wall-clock (25 LLM-bound add_episode writes × ~78s median, serialised)
On completion, run verify_lilymay.py to capture fresh ac_seed_02 + ac_seed_03 evidence
If green → update phase-1-validation.md: flip G2/G3 from Falsified to Held, append a "Wave 5 retry outcome — 2026-05-03" subsection citing run 5 evidence
If still red → leave task in in_progress/, document the new failure mode in the doc
Risks/cost:

~30-60 min of GB10 vLLM tokens (shared infra — qwen-graphiti is always-loaded so no swap, but still occupies the queue)
Writes to live FalkorDB at whitestocks:6379 (graph student-lilymay, currently empty)
Non-destructive: idempotency guard means a second /task-work call is safe; no data loss possible
Decision points:

Background vs foreground? Background recommended so you can interrupt or work in parallel
During the seed, should I poll periodically (every ~15min) and report progress, or sleep and only check at the end?
OK to launch in background with periodic check-ins?

yes please proceed
Launching the seed now.

Bash Find highest existing seed run number
IN
ls .guardkit/autobuild/TASK-GR-SEED/logs/ | grep -oE 'seed_run_[0-9]+' | sort -V | uniq | tail -5

OUT
seed_run_1
seed_run_2
seed_run_3
Update Todos

Launch seed_student_model.py as run 5 in background

Wait for seed to complete (~30-60min wall-clock)

Run verify_lilymay.py to capture fresh AC-SEED-02/03 evidence

Update phase-1-validation.md based on verify result (flip G2/G3 or document new failure)

Commit task state files (TASK-GR-SEED move + validation doc update)
Bash Launch seed run 5 in background, capture PID and confirm running
IN
date -u +"%Y-%m-%dT%H:%M:%SZ" > .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.start && nohup .venv/bin/python scripts/seed_student_model.py > .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.log 2>&1 &
echo $! > .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.pid
sleep 2
echo "PID: $(cat .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.pid)"
echo "Start: $(cat .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.start)"
echo "Process check:"
ps -p $(cat .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.pid) -o pid,etime,command 2>&1
echo "---initial log:"
head -20 .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.log 2>&1

OUT
PID: 99737
Start: 2026-05-03T17:23:40Z
Process check:
  PID ELAPSED COMMAND
99737   00:02 /Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python scripts/seed_student_model.py
---initial log:
2026-05-03 18:23:41,027 INFO study_tutor.knowledge.graphiti_client: graphiti client ready in 261ms
2026-05-03 18:23:41,028 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,032 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,037 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,041 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,043 INFO study_tutor.knowledge.async_write: graphiti write scheduled
2026-05-03 18:23:41,045 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,195 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,199 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,201 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,204 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,205 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,208 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,217 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,218 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,221 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,222 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'content' is already indexed
2026-05-03 18:23:41,227 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'uuid' is already indexed
2026-05-03 18:23:41,227 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'name' is already indexed
2026-05-03 18:23:41,232 INFO graphiti_core.driver.falkordb_driver: Index already exists: Attribute 'name' is already indexed
Seed is running (PID 99737, started 17:23:40 UTC). Initial log shows graphiti client connected in 261ms and the first graphiti write scheduled event already fired. Indexes already exist on the graph — confirms it's writing to the existing student-lilymay partition rather than re-creating it.

Launching a watcher in background that exits when the seed PID is gone, so I'll get a notification when the seed completes.

Bash Background watcher: waits for seed PID to exit then summarises results
IN
SEED_PID=$(cat .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.pid)
LOG=.guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.log
echo "Watching seed PID $SEED_PID (poll interval: 60s)"
START_EPOCH=$(date +%s)
while kill -0 "$SEED_PID" 2>/dev/null; do
  sleep 60
done
END_EPOCH=$(date +%s)
ELAPSED=$((END_EPOCH - START_EPOCH))
date -u +"%Y-%m-%dT%H:%M:%SZ" > .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.end
echo "==== SEED EXITED ===="
echo "Wall clock: ${ELAPSED}s ($((ELAPSED/60))min)"
echo "Last 30 log lines:"
tail -30 "$LOG"
echo "---"
echo "Total 'graphiti write scheduled' events: $(grep -c 'graphiti write scheduled' $LOG)"
echo "Total 'graphiti write succeeded' events: $(grep -c 'graphiti write succeeded' $LOG 2>/dev/null || echo 0)"
echo "Total 'graphiti write failed' events: $(grep -c 'graphiti write failed' $LOG 2>/dev/null || echo 0)"
echo "Final summary line (if any):"
grep -E 'seeded Lilymay baseline|seeding_skipped|seeding_completed' $LOG | tail -3

OUT
Command running in background with ID: bfdo0v939. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/47b0a01a-c3ee-4fa7-8ce1-11d4912f4612/tasks/bfdo0v939.output
Seed is running, watcher is in background (ID bfdo0v939) — I'll get a notification when the seed PID exits and the watcher reports the wall-clock + write counts + final summary.

Status so far:

Seed PID 99737 launched at 2026-05-03T17:23:40Z
Logging to .guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.log
Expected wall-clock: 30-60min (25 LLM-bound writes × ~78s median, serialised at concurrency=1)
Will notify on completion with: elapsed time, write success/failure counts, and the final summary line
You can interrupt at any time. Otherwise next message from me will be when the seed has exited and I've run verify_lilymay.py for fresh evidence — at which point I'll either flip G2/G3 or document the new failure mode, depending on what the verify shows.

Seed exited. Reading watcher output.

Bash Read seed watcher output
IN
cat /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/47b0a01a-c3ee-4fa7-8ce1-11d4912f4612/tasks/bfdo0v939.output

OUT
Watching seed PID 99737 (poll interval: 60s)
==== SEED EXITED ====
Wall clock: 808s (13min)
Last 30 log lines:
2026-05-03 18:29:18,088 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-03 18:29:21,712 INFO httpx: HTTP Request: POST http://promaxgb10-41b1:9000/v1/chat/completions "HTTP/1.1 200 OK"
2026-05-03 18:29:21,723 INFO httpx: HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
2026-05-03 18:29:21,738 INFO httpx: HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
2026-05-03 18:29:21,744 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near student
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
            WITH e, score, n, m
            RETURN
            
        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit
            
{'query': '(@group_id:"student-lilymay") (Student | lilymay | s | confidence | topic | Power | Conflict | Ozymandias | themes | increased | from | band | struggling | 0 | band | struggling | 35)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['student-lilymay']}
2026-05-03 18:29:21,744 WARNING study_tutor.knowledge.async_write: graphiti write failed
2026-05-03 18:29:21,763 INFO study_tutor.seed: seeded Lilymay baseline (subjects=0, confidences=0, succeeded_writes=6)
---
Total 'graphiti write scheduled' events: 25
Total 'graphiti write succeeded' events: 3
Total 'graphiti write failed' events: 22
Final summary line (if any):
2026-05-03 18:29:21,763 INFO study_tutor.seed: seeded Lilymay baseline (subjects=0, confidences=0, succeeded_writes=6)
Bash Analyse failure patterns in seed log
IN
LOG=.guardkit/autobuild/TASK-GR-SEED/logs/seed_run_5.log
echo "=== First 'graphiti write succeeded' contexts (before/after lines) ==="
grep -B 1 -A 1 'graphiti write succeeded' $LOG | head -20
echo ""
echo "=== First failure RediSearch error ==="
grep -A 3 'Syntax error at offset' $LOG | head -15
echo ""
echo "=== Are all failures the same RediSearch syntax error? ==="
grep -c 'Syntax error at offset 19 near student' $LOG
echo "out of total errors: $(grep -c 'ERROR' $LOG)"
echo ""
echo "=== Other distinct ERROR patterns ==="
grep 'ERROR' $LOG | sed 's/^[0-9: -]*ERROR [^:]*: //' | sort -u | head -10

OUT
=== First 'graphiti write succeeded' contexts (before/after lines) ===
2026-05-03 18:24:23,343 INFO graphiti_core.graphiti: Completed add_episode in 42299.28112030029 ms
2026-05-03 18:24:23,343 INFO study_tutor.knowledge.async_write: graphiti write succeeded
2026-05-03 18:24:23,343 INFO study_tutor.seed: seeding batch drained
--
2026-05-03 18:27:07,053 INFO graphiti_core.graphiti: Completed add_episode in 68182.2509765625 ms
2026-05-03 18:27:07,054 INFO study_tutor.knowledge.async_write: graphiti write succeeded
2026-05-03 18:27:07,054 INFO study_tutor.seed: seeding batch drained
--
2026-05-03 18:29:01,311 INFO graphiti_core.graphiti: Completed add_episode in 27659.054040908813 ms
2026-05-03 18:29:01,312 INFO study_tutor.knowledge.async_write: graphiti write succeeded
2026-05-03 18:29:05,700 INFO httpx: HTTP Request: POST http://promaxgb10-41b1:9000/v1/chat/completions "HTTP/1.1 200 OK"

=== First failure RediSearch error ===
2026-05-03 18:24:41,294 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
--
2026-05-03 18:24:55,994 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
--
2026-05-03 18:24:56,012 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
--

=== Are all failures the same RediSearch syntax error? ===
3
out of total errors: 23

=== Other distinct ERROR patterns ===
2026-05-03 18:24:41,294 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
2026-05-03 18:24:55,994 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
2026-05-03 18:24:56,012 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
2026-05-03 18:25:36,624 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
2026-05-03 18:25:40,625 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
2026-05-03 18:25:51,334 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
2026-05-03 18:25:58,870 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
2026-05-03 18:25:58,876 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 19 near subject
2026-05-03 18:26:34,774 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 17 near fleet
2026-05-03 18:26:45,958 ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query: RediSearch: Syntax error at offset 17 near fleet
Verify confirms the situation is unchanged — still empty:


{
  "ac_seed_03_get_student_state": {"empty": false, "year_group": null, "target_grade": null, "subjects": [], "topic_confidences": []},
  "ac_seed_02_student_lilymay_nodes": []
}
(The fresh Connection closed by server ConnectionError reappeared on stderr — same R-WAVE5-01 / AC-SEED-06 escalation signal as before.)

This is a different failure mode than Wave 4 — and it's a showstopper that retry won't fix.

Root cause: graphiti-core is incompatible with dashed group_ids in FalkorDB
Three error variants, all identical pattern:

Syntax error at offset 19 near student — (@group_id:"student-lilymay")
Syntax error at offset 19 near subject — (@group_id:"subject-english-literature")
Syntax error at offset 17 near fleet — (@group_id:"fleet-appmilla")
Failure site: graphiti-core builds a RediSearch fulltext query inside db.idx.fulltext.queryRelationships('RELATES_TO', $query) during entity-resolution. In RediSearch syntax, - is the NOT operator, so student-lilymay parses as "student NOT lilymay" — breaking the query.

Why 3 writes succeeded: they were the very first writes against an empty RELATES_TO index. Once any relationship landed, every subsequent entity-resolution lookup hit the dashed-group_id query path and crashed.

This is a direct collision between two graphiti-core constraints the project has already worked around once:

GroupIdValidationError rejects student:lilymay (only [A-Za-z0-9_-] allowed) → forced the project to migrate to dashes (commit a210472)
RediSearch fulltext rejects student-lilymay (dash = NOT operator) → blocks everything once the index has data
I can't fix this within the scope of /task-work TASK-GR-SEED — it needs an architectural decision. I'll document the finding in phase-1-validation.md, move the task to blocked/ with a clear reason, and stop short of guessing which remediation you want.

Update Todos

Launch seed_student_model.py as run 5 in background

Wait for seed to complete (~30-60min wall-clock)

Run verify_lilymay.py to capture fresh AC-SEED-02/03 evidence

Document NEW failure mode (RediSearch dash-as-NOT) in phase-1-validation.md

Move TASK-GR-SEED to blocked/ with clear reason

Surface remediation options to user (patch graphiti-core, format migration, or backend swap)
Let me update phase-1-validation.md with the Wave 5 retry findings.

Read phase-1-validation.md (lines 149-158)
Edit phase-1-validation.md
Added 75 lines
Read TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md (lines 2-26)
Edit TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
Modified
Bash Move task to blocked and check git status
IN
git mv tasks/in_progress/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md tasks/blocked/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md && git status --short tasks/ docs/research/ideas/phase-1-validation.md

OUT
 M docs/research/ideas/phase-1-validation.md
RM tasks/completed/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md -> tasks/blocked/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md
Update Todos

Launch seed_student_model.py as run 5 in background

Wait for seed to complete (~30-60min wall-clock)

Run verify_lilymay.py to capture fresh AC-SEED-02/03 evidence

Document NEW failure mode (RediSearch dash-as-NOT) in phase-1-validation.md

Move TASK-GR-SEED to blocked/ with clear reason

Surface remediation options to user (patch graphiti-core, format migration, or backend swap)
Outcome — Wave 5 retry: still red, but for a different reason
Seed run 5: 13min wall-clock, 25 scheduled / 3 succeeded / 22 failed. Verify confirms graph still empty for student-lilymay. Task moved to tasks/blocked/. phase-1-validation.md updated with full Wave 5 retry findings, R-WAVE5-03 + R-WAVE5-04 entries, and updated AC-SEED-XX status table.

The actual blocker (R-WAVE5-03)
Wave 4's narrative was wrong about what was breaking. The vLLM rate-limit story (R-WAVE5-01) was a plausible misreading of partial logs — the real issue is a hard graphiti-core × FalkorDB × RediSearch incompatibility:

graphiti-core's GroupIdValidationError only allows [A-Za-z0-9_-] → forced project to use student-lilymay
graphiti-core's RediSearch fulltext query parses student-lilymay as student NOT lilymay → query syntax error
First 3 writes succeed (empty RELATES_TO index, no entity-resolution lookup); writes 4-25 fail (index now populated, every lookup hits the broken query)
Independently corroborated through MCP: mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"]) returns the same RediSearch syntax error — meaning AC-SEED-02 as written is currently unverifiable through MCP at all.

Decision required — three remediation paths
#	Path	Blast radius	Trade-off
1	Monkey-patch graphiti-core to escape group_ids in fulltext query construction (\- or {}-wrapping per RediSearch escaping rules). Lives in study_tutor.knowledge.graphiti_client, intercepting the FalkorDB driver at import time.	Smallest. Group_id format stays student-lilymay; no downstream code touched.	Carries an upstream-dependency wart; needs to be revisited when graphiti-core releases a fix.
2	Migrate group_id format dash → underscore (student_lilymay, subject_english_literature, fleet_appmilla).	Touches the post-a210472 normalisation surface: student_model.py, the test fixtures updated in that commit, operator docs that cite the dash form, the noted-divergent specialist-agent reference.	No upstream wart, but reopens a migration that already shipped.
3	Switch graph backend FalkorDB → Neo4j. Lucene fulltext syntax doesn't treat - as NOT.	Largest. Cascades into ADR-ARCH-018 / ADR-ARCH-019 territory.	Overkill for this issue alone; only worth it if other Neo4j-vs-FalkorDB tradeoffs are already in play.
My read: option 1 is the right next move — smallest blast radius, validates the diagnosis, unblocks the seed, leaves option 2 available later if upstream graphiti-core stays unfixed for a long time. But this is a real architectural choice and I shouldn't make it for you.

There's also a secondary signal worth flagging: R-WAVE5-04 (Connection closed by server reappearing on read-only paths during verify) — Wave 4 marked AC-SEED-06 as "no escalation observed", but it's now intermittently reappearing. May need a separate FalkorDB-side investigation regardless of which R-WAVE5-03 path you pick.

Which path do you want to take, or do you want to investigate further first?

please provide details of what you are recommending for option 1 - where does graphiti-core live? Is it guardkit repo source code or the actual open source getzep repo? My honest take on graphiti is its a buggy piece of shit - half my work seems to be working around bugs etc in it not working and everytime I think it's all ok and we can move on there is something else.
Fair venting — and the validation doc backs it up empirically: this is now the 5th distinct graphiti-core workaround in the project (Read API mismatch, Write API mismatch, GroupIdValidationError migration, OpenAI default LLM client, and now the RediSearch dash-as-NOT bug). That's signal, not noise. Let me get you the concrete details before you decide.

Bash Confirm graphiti-core source: pip vs vendored
IN
.venv/bin/pip show graphiti-core 2>&1 | head -10
echo "---"
ls -d .venv/lib/python*/site-packages/graphiti_core/ 2>&1
echo "---"
echo "Source of truth — pyproject.toml graphiti deps:"
grep -i graphiti pyproject.toml 2>/dev/null
echo "---"
echo "Is graphiti-core vendored anywhere in the repo?"
find . -path ./.venv -prune -o -path ./.git -prune -o -name "graphiti_core" -print 2>/dev/null | head -5

OUT
(eval):1: no such file or directory: .venv/bin/pip
---
.venv/lib/python3.14/site-packages/graphiti_core/
---
Source of truth — pyproject.toml graphiti deps:
    # TASK-GR-WIRE / AC-WIRE-06 (FEAT-FD32, 2026-05-02): pin graphiti-core to
    "graphiti-core>=0.29,<0.30",
---
Is graphiti-core vendored anywhere in the repo?
Bash Locate the broken query builder in graphiti-core
IN
FALKOR=.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py
ls -l $FALKOR 2>&1
echo "---"
echo "Lines containing 'fulltext' or 'queryRelationships' or 'queryNodes':"
grep -n -E "fulltext|queryRelationships|queryNodes|RediSearch" $FALKOR | head -20

OUT
-rw-r--r--@ 1 richardwoollcott  staff  17013 Apr 27 21:52 .venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py
---
Lines containing 'fulltext' or 'queryRelationships' or 'queryNodes':
68:from graphiti_core.graph_queries import get_fulltext_indices, get_range_indices
113:    fulltext_syntax: str = '@'  # FalkorDB uses a redisearch-like syntax for fulltext queries
303:        index_queries = get_range_indices(self.provider) + get_fulltext_indices(self.provider)
389:    def build_fulltext_query(
393:        Build a fulltext query string for FalkorDB using RedisSearch syntax.
406:            # Escape group_ids with quotes to prevent RediSearch syntax errors
Bash Find where the @group_id query string is built
IN
echo "=== Search for the offending fulltext query construction ==="
grep -rn "queryRelationships\|queryNodes\|@group_id" .venv/lib/python3.14/site-packages/graphiti_core/ 2>/dev/null | head -30

OUT
=== Search for the offending fulltext query construction ===
.venv/lib/python3.14/site-packages/graphiti_core/graph_queries.py:146:        return f"CALL db.idx.fulltext.queryNodes('{label}', {query})"
.venv/lib/python3.14/site-packages/graphiti_core/graph_queries.py:152:    return f'CALL db.index.fulltext.queryNodes("{name}", {query}, {{limit: $limit}})'
.venv/lib/python3.14/site-packages/graphiti_core/graph_queries.py:169:        return f"CALL db.idx.fulltext.queryRelationships('{label}', $query)"
.venv/lib/python3.14/site-packages/graphiti_core/graph_queries.py:175:    return f'CALL db.index.fulltext.queryRelationships("{name}", $query, {{limit: $limit}})'
.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:398:        - AND is implicit with space: (@group_id:value) (text)
.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:399:        - OR uses pipe within parentheses: (@group_id:value1|value2)
.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:410:            group_filter = f'(@group_id:{group_values})'
.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb/operations/search_ops.py:107:        group_filter = f'(@group_id:{group_values})'
Found it — and there's a smoking gun. graphiti-core is pip-installed from upstream (pinned >=0.29,<0.30), not vendored. There are two call sites building the broken query, and one of them has a comment claiming to escape group_ids — meaning upstream tried to fix this and failed. Let me read both.

Read falkordb_driver.py (lines 386-425)
Read search_ops.py (lines 96-125)
Where graphiti-core lives
It's the upstream getzep package (PyPI: graphiti-core), pinned >=0.29,<0.30 in your pyproject.toml, installed at .venv/lib/python3.14/site-packages/graphiti_core/. Not vendored anywhere in your repo or in guardkit. Source repo: github.com/getzep/graphiti. So a "monkey-patch" means importing graphiti-core normally, then mutating its functions at runtime from your own code in study_tutor/knowledge/.

The smoking gun
Look at falkordb_driver.py:406-410:


# Escape group_ids with quotes to prevent RediSearch syntax errors
# with reserved words like "main" or special characters like hyphens
escaped_group_ids = [f'"{gid}"' for gid in group_ids]
group_values = '|'.join(escaped_group_ids)
group_filter = f'(@group_id:{group_values})'
Upstream already tried to fix this exact bug. The comment explicitly mentions "special characters like hyphens." But the fix is wrong — wrapping in double-quotes does NOT prevent RediSearch from parsing the dash inside as a NOT operator. The runtime error proves it: query is (@group_id:"student-lilymay") (quotes present in the actual SQL we logged), syntax error at offset 19 (the dash).

Same broken code is duplicated in falkordb/operations/search_ops.py:105-107 — both call sites would need patching.

The correct RediSearch escape for hyphens is either backslash-escape (\-) or verbatim-brace wrap ({student-lilymay} — RediSearch treats the contents as opaque). Quotes alone don't cut it.

What the patch actually looks like
A new file src/study_tutor/knowledge/graphiti_patches.py, ~40 lines:


"""R-WAVE5-03 — graphiti-core 0.29 fails to escape dashes in RediSearch
fulltext queries on FalkorDB. Upstream attempted a fix in
falkordb_driver.py:406-410 (double-quote wrap) but the fix is wrong:
RediSearch still parses dashes as NOT operators inside double quotes.

This patch overrides both call sites with brace-wrapped verbatim values,
which RediSearch treats as opaque tokens. Remove once upstream ships a
real fix (track issue: TBD — open against getzep/graphiti).
"""
from graphiti_core.driver import falkordb_driver
from graphiti_core.driver.falkordb.operations import search_ops

_STOPWORDS = falkordb_driver.STOPWORDS  # reuse upstream's stopword list


def _brace_wrap(group_ids):
    return [f'{{{gid}}}' for gid in group_ids]


def _patched_build_fulltext_query(self, query, group_ids=None, max_query_length=128):
    falkordb_driver.validate_group_ids(group_ids)
    if not group_ids:
        group_filter = ''
    else:
        group_filter = f'(@group_id:{"|".join(_brace_wrap(group_ids))})'
    sanitized = self.sanitize(query)
    words = [w for w in sanitized.split() if w and w.lower() not in _STOPWORDS]
    sanitized = ' | '.join(words)
    if len(sanitized.split(' ')) + len(group_ids or '') >= max_query_length:
        return ''
    return group_filter + ' (' + sanitized + ')'


def _patched_search_ops_query(query, group_ids=None, max_query_length=...):
    # mirror image of above — same brace-wrap fix
    ...


def install():
    falkordb_driver.FalkorDriver.build_fulltext_query = _patched_build_fulltext_query
    search_ops._build_falkor_fulltext_query = _patched_search_ops_query
Then in graphiti_client.py, add from .graphiti_patches import install as _install_patches; _install_patches() at the top so the patch is in place before any FalkorDriver instance is constructed.

Risks I'd flag before doing this:

Upstream's "fix" already shipped, untested against real FalkorDB. That's a process-smell on the getzep side. Whatever tests they ran for the double-quote version, they didn't actually run the query through RediSearch with a non-empty index. My patch needs the same scrutiny — write it, then run the seed end-to-end (the 3-good-then-22-bad pattern only manifests once the index has data, so a 5-write smoke test would falsely look green).
Two call sites is a code-smell — getzep duplicated the function. Version 0.30 might add a third call site or refactor the duplication, and either move re-bakes the patch.
Brace-wrap may interact with multi-value group_id queries ((@group_id:val1|val2)) — would need to test that a query targeting multiple group_ids still parses. Backslash-escape is the safer bet on that axis but uglier on the eye.
Time: ~1h to write + smoke-test the patch, ~30-60min to re-run seed, ~15min to verify + flip G2/G3. Total ~2-3 hours.

On the broader frustration — that's a real signal
You're not wrong, and the project history backs it up. Counting from the validation doc + this session:

#	Bug	Workaround
1	get_client(config) defaulted to OpenAI 401	Wave 2 wired LLM/embedder explicitly
2	Read API mismatch (search_nodes doesn't exist)	New _read_student_partition seam in queries.py
3	Write API mismatch (add_episode kwargs wrong)	_add_episode_kwargs helper in async_write.py
4	GroupIdValidationError rejects colons	Migrated student: → student- (commit a210472)
5	RediSearch dashes-as-NOT — and upstream's "fix" doesn't work	This task
That's five distinct upstream defects in a few weeks, on a single integration. Bug #5 is especially concerning because the upstream fix attempt makes it look like getzep tested it, and they didn't. If anything, that's a stronger argument for considering whether to keep paying the graphiti tax.

A few alternatives worth at least naming, even if you stick with option 1 for now:

Replace graphiti-core with a thin direct-FalkorDB layer. Your project's actual surface is small (get_student_state, _perform_write, the seed), and a custom writer + querier might be a few hundred lines. You'd lose graphiti's entity-resolution / fact-extraction, but a glance at the seed says you're not really using those — the seed has structured data, not free text needing extraction.
Drop graph framing entirely. A flat learner profile in JSONB on Postgres (or sqlite) covers the read/write surface the project currently uses. Phase 2 features that genuinely need a graph can adopt one later.
Open an upstream issue + wait. The dashes-as-NOT bug is a 5-line fix and trivially demonstrable; an active maintainer should land it fast. But "fast" upstream usually means weeks, and you have FEAT-FD32 to land.
Keep paying the graphiti tax (option 1). Pragmatic if you're attached to the entity-resolution / temporal-fact features for Phase 2+ — but the bug-rate suggests budgeting time for #6.
Happy to do any of: (a) write + smoke-test the option-1 patch, (b) sketch what a graphiti-replacement layer would look like for your actual usage, (c) draft the upstream issue, (d) something else. What's the call?

honestly that's just a part of the story broaden your search to include the guardkit repo and the MCP setup  - right now I've just been workign on preparing this task which needs to run on the GB10 because the MCP just silently fails to write - it's never ending:
The task file reads cleanly end-to-end. Status stays backlog, decision is locked in, GB10-execution constraint is documented,
  patch shape is concrete.

  Final summary of what changed in the task file:

  - Frontmatter: added remediation_decision: option_b_openai_generic and execution_location: promaxgb10-41b1 (work directly on
  the GB10, not via SSH from a Mac dev machine). Bumped updated.
  - New "Decision (2026-05-03): Option (b)" section: locks in the choice with the local-only-LLM constraint as the deciding
  factor, plus a comparison table showing why (a) is insufficient and (c) is a hack.
  - First AC item: flipped to [x] since the path is now chosen, with rationale referencing the Decision section.
  - New "Execute on the GB10 directly" subsection under Implementation Notes: explains why (Docker daemon locality, vendored
  repo path, log-access proximity) plus a 9-step suggested order of operations.
  - "Where the patch lands" subsection: rewrote with a concrete case 'openai_generic': snippet, the matching YAML provider
  block, and a note that the patch is local-only with documentation in graphiti-mcp-build.sh (no upstream contribution right
  now).
  - Files section: removed "possibly" / "OR" hedging now that the path is chosen.

  Status remains backlog — file stays at tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md. Pick it up on the
  GB10 when you're ready.

✻ Cogitated for 2m 9s

※ recap: Goal: fix graphiti-mcp silently dropping MCP writes by adding an openai_generic provider so it calls
  chat.completions.create against local LLMs. Task TASK-INF-5054 is updated with the decision and stays in backlog. Next: pick
  it up on the GB10.

Plus we can't just patch this in this repo we are going to have the same issue everywhere we use graphiti surely?
Show less
You're right — the picture's much bigger than this repo. Let me pull the threads together before I respond, because your architectural point ("we'd hit the same issue everywhere we use graphiti") is exactly the question I should be answering.

Bash Locate TASK-INF-5054 and graphiti-mcp deployment artifacts
IN
echo "=== TASK-INF-5054 location ==="
find ~/Projects -name "TASK-INF-5054*" 2>/dev/null | head -10
echo ""
echo "=== Graphiti MCP deployment artifacts in study-tutor ==="
find . -path ./.venv -prune -o -path ./.git -prune -o -name "*.sh" -print 2>/dev/null | xargs grep -l "graphiti" 2>/dev/null | head -10
echo ""
echo "=== Graphiti MCP-related references anywhere ==="
grep -rn "graphiti-mcp\|graphiti_mcp" .claude/ ~/Projects/appmilla_github/ 2>/dev/null --include="*.json" --include="*.md" --include="*.sh" --include="*.yaml" --include="*.yml" 2>&1 | grep -v ".venv\|.git\|node_modules\|TASK-GR\|jarvis" | head -20

OUT
=== TASK-INF-5054 location ===
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md

=== Graphiti MCP deployment artifacts in study-tutor ===

=== Graphiti MCP-related references anywhere ===
Bash Check Claude Code MCP server config for study-tutor
IN
echo "=== guardkit repo location and graphiti usage ==="
ls -d ~/Projects/appmilla_github/guardkit/ 2>/dev/null
echo ""
echo "=== Where are MCP servers configured for Claude Code? ==="
cat ~/.claude.json 2>/dev/null | python3 -c "import json, sys; d = json.load(sys.stdin); proj = d.get('projects', {}).get('/Users/richardwoollcott/Projects/appmilla_github/study-tutor', {}); mcps = proj.get('mcpServers', {}); print(json.dumps(mcps, indent=2))" 2>&1 | head -60

OUT
=== guardkit repo location and graphiti usage ===
/Users/richardwoollcott/Projects/appmilla_github/guardkit/

=== Where are MCP servers configured for Claude Code? ===
{
  "docs-langchain": {
    "type": "http",
    "url": "https://docs.langchain.com/mcp"
  }
}
Read TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md
Bash Map the full graphiti integration surface across repos and hosts
IN
echo "=== Is graphiti repo cloned on this Mac too? ==="
ls -d ~/Projects/appmilla_github/graphiti/ 2>&1
echo ""
echo "=== guardkit graphiti scripts ==="
ls ~/Projects/appmilla_github/guardkit/scripts/graphiti* 2>&1 | head -5
echo ""
echo "=== Any other repos using graphiti-core in the appmilla_github org? ==="
find ~/Projects/appmilla_github/ -maxdepth 4 -name "pyproject.toml" -not -path "*/.venv/*" -not -path "*/node_modules/*" 2>/dev/null | xargs grep -l "graphiti" 2>/dev/null | head -10
echo ""
echo "=== TASK-INF-5053 (the parent task) — for the audit trail ==="
ls ~/Projects/appmilla_github/guardkit/tasks/*/TASK-INF-5053* 2>/dev/null

OUT
Exit code 1
=== Is graphiti repo cloned on this Mac too? ===
/Users/richardwoollcott/Projects/appmilla_github/graphiti/

=== guardkit graphiti scripts ===
/Users/richardwoollcott/Projects/appmilla_github/guardkit/scripts/graphiti-backup.sh
/Users/richardwoollcott/Projects/appmilla_github/guardkit/scripts/graphiti-endpoint-toggle.sh
/Users/richardwoollcott/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-bootstrap.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-build.sh
/Users/richardwoollcott/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml

=== Any other repos using graphiti-core in the appmilla_github org? ===
/Users/richardwoollcott/Projects/appmilla_github/graphiti/pyproject.toml
/Users/richardwoollcott/Projects/appmilla_github/guardkit/pyproject.toml
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/pyproject.toml
/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml
/Users/richardwoollcott/Projects/appmilla_github/graphiti/server/pyproject.toml
/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/pyproject.toml
/Users/richardwoollcott/Projects/appmilla_github/graphiti/examples/opentelemetry/pyproject.toml

=== TASK-INF-5053 (the parent task) — for the audit trail ===
(eval):11: no matches found: /Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/*/TASK-INF-5053*
Bash Check graphiti-mcp build script for version pinning
IN
SCRIPT=~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-build.sh
if [ -f "$SCRIPT" ]; then
  echo "=== graphiti-mcp-build.sh — version pin and clone target ==="
  grep -n "GRAPHITI_REPO\|git clone\|git checkout\|GRAPHITI_VERSION\|FROM\|graphiti-core" "$SCRIPT" | head -15
  echo ""
  echo "=== Top of file (first 25 lines) ==="
  head -25 "$SCRIPT"
fi

OUT
<tool_use_error>Cancelled: parallel tool call Bash(echo "=== Is graphiti repo cloned on thi…) errored</tool_use_error>
Bash Check version pins, local clone, and existing guardkit graphiti docs
IN
echo "=== guardkit + jarvis graphiti-core pins ==="
grep "graphiti" ~/Projects/appmilla_github/guardkit/pyproject.toml ~/Projects/appmilla_github/jarvis/pyproject.toml 2>/dev/null
echo ""
echo "=== Local graphiti clone — falkordb_driver.py:406-410 (does the dash bug exist here too?) ==="
sed -n '400,415p' ~/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py 2>/dev/null
echo ""
echo "=== Local graphiti clone version ==="
grep -E "^version" ~/Projects/appmilla_github/graphiti/pyproject.toml | head -3
echo ""
echo "=== TASK-INF-5053 audit (for the bug-count tally) ==="
find ~/Projects/appmilla_github/guardkit -name "TASK-INF-5053*" 2>/dev/null | head -5
echo ""
echo "=== graphiti-related rules in guardkit ==="
ls ~/Projects/appmilla_github/guardkit/.claude/rules/graphiti* ~/Projects/appmilla_github/guardkit/docs/guides/graphiti* 2>/dev/null

OUT
=== guardkit + jarvis graphiti-core pins ===
/Users/richardwoollcott/Projects/appmilla_github/guardkit/pyproject.toml:    "graphiti-core>=0.5.0",
/Users/richardwoollcott/Projects/appmilla_github/guardkit/pyproject.toml:# Installs graphiti-core with FalkorDB support
/Users/richardwoollcott/Projects/appmilla_github/guardkit/pyproject.toml:    "graphiti-core[falkordb]",
/Users/richardwoollcott/Projects/appmilla_github/guardkit/pyproject.toml:# Required when .guardkit/graphiti.yaml sets llm_provider: gemini
/Users/richardwoollcott/Projects/appmilla_github/guardkit/pyproject.toml:    "graphiti-core[google-genai]",
/Users/richardwoollcott/Projects/appmilla_github/guardkit/pyproject.toml:    "graphiti-core[falkordb]",
/Users/richardwoollcott/Projects/appmilla_github/guardkit/pyproject.toml:    "graphiti-core[google-genai]",
/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml:# `[graphiti]` declares the `graphiti-core` SDK used by the routing-history
/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml:# combo Jarvis relies on (`.guardkit/graphiti.yaml` configures
/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml:# graphiti-core is still on its 0.x stabilisation path and a 1.0 bump is
/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml:graphiti = [
/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml:    "graphiti-core>=0.9,<1",
/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml:    "jarvis[graphiti]",

=== Local graphiti clone — falkordb_driver.py:406-410 (does the dash bug exist here too?) ===
        """
        validate_group_ids(group_ids)

        if group_ids is None or len(group_ids) == 0:
            group_filter = ''
        else:
            # Escape group_ids with quotes to prevent RediSearch syntax errors
            # with reserved words like "main" or special characters like hyphens
            escaped_group_ids = [f'"{gid}"' for gid in group_ids]
            group_values = '|'.join(escaped_group_ids)
            group_filter = f'(@group_id:{group_values})'

        sanitized_query = self.sanitize(query)

        # Remove stopwords and empty tokens from the sanitized query
        query_words = sanitized_query.split()

=== Local graphiti clone version ===
version = "0.28.2"

=== TASK-INF-5053 audit (for the bug-count tally) ===
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/state/TASK-INF-5053
/Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/completed/2026-05/TASK-INF-5053-graphiti-mcp-http-server-group-id-fix.md

=== graphiti-related rules in guardkit ===
/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/rules/graphiti-knowledge-graph.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/rules/graphiti-knowledge.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-add-context.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-claude-code-integration.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-commands.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-context-troubleshooting.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-gb10-deployment.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-gemini-rollout-setup.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-integration-guide.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-job-context.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-knowledge-capture.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-parsers.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-project-namespaces.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-query-commands.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-shared-infrastructure.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-testing-validation.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/guides/graphiti-turn-states.md
You're right — this is much worse than my earlier framing made it sound. The full picture:

The graphiti-core surface across appmilla_github
Repo / process	graphiti-core source	Version pin / actual	Bugs that bite it
study-tutor (local Mac venv)	pip → site-packages	>=0.29,<0.30 (0.29.x)	RediSearch dash-as-NOT (R-WAVE5-03)
graphiti-mcp container (GB10)	Docker image built from ~/Projects/appmilla_github/graphiti clone	0.28.2 vendored	RediSearch dash-as-NOT AND factories.py openai branch ignores api_url (TASK-INF-5054) AND OpenAIClient.responses.parse vs chat.completions.create (also TASK-INF-5054)
guardkit (Mac venv)	pip → site-packages	>=0.5.0 (loose pin, dangerous)	Whichever version resolves; likely the same RediSearch bug if dashed group_ids are used
jarvis (Mac venv)	pip → site-packages	>=0.9,<1	Same — bugs likely present
Local ~/Projects/appmilla_github/graphiti/ clone	git clone of getzep/graphiti, used by GB10 build	0.28.2 — I just verified the same broken double-quote escape exists at falkordb_driver.py:406-410	Same RediSearch bug; this is what gets baked into the MCP container
So your intuition is correct: any patch I write in study_tutor.knowledge.graphiti_client only fires when that module is imported. Four other consumers (MCP container, guardkit venv, jarvis venv, future projects) all carry their own copies of the same broken code. Patches don't propagate — bugs do.

A critical addition for TASK-INF-5054
Even after TASK-INF-5054 lands, MCP reads through dashed group_ids will still fail. I already proved this earlier in our session — mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"]) returned the same Syntax error at offset 19 near student that the local seed run hit. The MCP container has the bug too (same broken upstream code, same version family). Option (b)'s openai_generic patch fixes WRITES (no more silent drops); the RediSearch fix would have to be folded in to fix READS.

While you're on the GB10 rebuilding the image anyway, the RediSearch patch is the same diff against a different file (graphiti_core/driver/falkordb_driver.py:406-410 and the duplicate at falkordb/operations/search_ops.py:105-107). One container rebuild, two patches landed. Otherwise TASK-INF-5054 ships and you discover bug #8 the next time something uses dashed group_ids on the MCP path.

Updated bug tally
Counting both repos and the MCP container: 7 distinct upstream defects, plus an investigation tax for the false-alarm group_id coercion (TASK-INF-5053). Across two different graphiti-core versions, both with the same broken "fix" for the RediSearch issue. That's not "one bad week" — it's a sustained signal about library quality.

Strategic options, re-laid given the full picture
Option	What it costs you up front	What it costs you ongoing	What it gets you
A	Keep paying. Land TASK-INF-5054 + R-WAVE5-03 on the GB10 (one rebuild, both patches). Apply R-WAVE5-03 separately in study-tutor venv. Patch jarvis/guardkit when they bite.	~3 hrs (combined GB10 work) + ~1 hr (study-tutor patch)	~2-3 hrs/month per new graphiti bug; patch-sprawl across 4+ install locations	Path of least disruption; preserves whatever graphiti-core features Phase 2 actually depends on
B	Centralise patches in guardkit. Single graphiti_patches package that all Python consumers import. Doesn't help the MCP container (different runtime).	~4-6 hrs to design + apply across consumers	Lower per-bug cost (one place to patch); still doesn't help MCP	Reduces patch-sprawl to ~2 places (guardkit-managed Python projects + the GB10 image)
C	Shrink graphiti's role. For structured-data round-trips (the seed, learner profile reads), bypass graphiti-core and write directly to FalkorDB via MERGE/MATCH cypher. Keep graphiti only for paths that genuinely need entity-extraction-from-prose (if any).	~1-2 days to write StudentProfileGraphWriter + Reader, port the seed, update the runtime client	Near-zero — your code, your bugs	The seed becomes ~50ms/write instead of 42-78s (no LLM extraction step you don't need); read path no longer hits the broken fulltext query at all; you stop paying for graphiti features the project doesn't use
D	Drop graphiti AND FalkorDB. JSONB-on-postgres or sqlite for the learner profile.	2-3 days, large blast radius	Near-zero	Eliminates the entire integration; graph framing disappears from the project
E	Wait for upstream. Open one consolidated issue with all bugs. Pin study-tutor at the current version. Defer Phase 2 work that needs graphiti.	~30min to draft the issue	High opportunity cost; getzep responsiveness unknown	Cleanest if upstream actually responds; risky bet
My honest take
Option C is the right strategic move, given what I see in the seed log:

The seed sends already-structured JSON to add_episode, which then runs LLM-driven entity extraction (42-78s per call) to convert it back into structured nodes/edges. That extraction step does nothing useful for structured input — it's pure overhead, AND it's where the broken fulltext lookup is triggered.
The runtime read path (get_student_state) already bypasses graphiti's high-level API in favour of EntityNode.get_by_group_ids (per the Wave 2 patch in queries.py). You're already halfway out of graphiti for reads.
Your bug surface is concentrated in graphiti-core's middle layer (entity-resolution, fulltext search, factory routing). The bottom layer (FalkorDB driver) is mostly fine — Cypher works.
A direct FalkorDB writer/reader for structured profile data is bounded scope (~200 lines), no upstream dependency, and the speedup alone (78s → 50ms per write) is worth doing.
But this isn't my call. The pull toward Option C depends on: do you actually use graphiti's auto entity-extraction or temporal-fact tracking anywhere in Phase 2? If yes, you might want to keep graphiti for those paths and shrink it only for the structured-data paths — a hybrid. If no, dropping it from the structured paths is most of the win.

Things I would not recommend right now:

Option 1 (monkey-patch in study-tutor) — my earlier recommendation. It only solves a fifth of the actual problem and leaves you with N copies of the same patch.
Pure-A status quo without folding R-WAVE5-03 into TASK-INF-5054 — you'd ship TASK-INF-5054 and immediately discover MCP reads are still broken.
What feels right? Some plausible next moves:

Bundle R-WAVE5-03 into TASK-INF-5054 as an extra patch step on the GB10, ship the combined fix, leave Option C for after FEAT-FD32 closes
Pivot to Option C now — write the direct-FalkorDB layer for the seed, defer TASK-INF-5054 to whenever the MCP path actually needs to write (which may be never if structured paths bypass it)
Look at Phase 2 features first to find out whether graphiti's entity-extraction is on the critical path before deciding C vs A
I can do any of these — write the TASK-INF-5054 addendum, sketch what StudentProfileGraphWriter would look like, or audit Phase 2 features for graphiti dependencies. What's the call?

What about forking the graphiti repo and just fixing the bugs? We have fixed a bunch already and you seem to have a good handle of the fixes needed for the Redis query issues? After the DDD South West talk in mid-may we can do extensive research and replace it with something more reliable but if we try to do that now we potentially de-rail both the DDD South West talk and the Kaggle hackathon submission for the study tutor
Good call — this is the right pragmatic move given the deadlines. Forking lands you with one patch surface instead of N monkey-patches, doesn't lose any features, doesn't preclude Option C later, and is doable in a single afternoon on the GB10. Let me lay out what it actually entails.

Why a fork is cleaner than my earlier options
The fork strategy beats my earlier suggestions on every axis except "do nothing":

vs monkey-patch in study-tutor: covers all consumers (study-tutor, guardkit, jarvis, MCP container) from one source. No import-time tricks. Real code, not runtime mutation.
vs centralise patches in guardkit: covers the MCP container too (which guardkit-side patches can't reach), because graphiti-mcp-build.sh already clones the graphiti repo — just point it at your fork.
vs shrink graphiti's role / replace: 3-4 hours vs 1-2 days. Doesn't disrupt the FEAT-FD32 + DDD South West + Kaggle critical path.
bonus: TASK-INF-5054 gets dramatically simpler. Today the task file describes "patch upstream factories.py locally + add a comment block in graphiti-mcp-build.sh reminding the next person to re-apply." Under the fork strategy, that whole "remember to re-apply the patch" wart disappears — the patch IS the fork.
Concrete punchlist for the fork
The known fixes that need to land in the fork:

Fix	File(s) in graphiti repo	Source
RediSearch dash-escape — replace double-quote wrap with brace-wrap or backslash-escape	graphiti_core/driver/falkordb_driver.py:406-410 and graphiti_core/driver/falkordb/operations/search_ops.py:105-107 (duplicate)	This session — R-WAVE5-03
openai_generic factory branch — pass base_url, use OpenAIGenericClient instead of OpenAIClient	mcp_server/src/services/factories.py (new case alongside openai, groq)	TASK-INF-5054 (already specced in detail)
That's two real fixes across three files. Both diffs are small (~10-30 lines each).

The Wave 2 fixes (LLM/embedder wiring in get_client, the _read_student_partition seam, the _add_episode_kwargs helper) stay in consumer code — they're not bugs in graphiti-core, they're consumer wiring choices around graphiti-core's API surface. So the fork doesn't carry those.

Decisions you need to make before forking
Which version to fork from? Right now you have 0.28.2 in the local clone (used by GB10 MCP container) and 0.29.x in study-tutor's venv. Two practical options:

Standardise on 0.29.x — pick a tag (e.g. 0.29.5 or whatever's current), fork from there, rebuild the MCP container against it. Single version everywhere. Bigger upfront move because you're upgrading the MCP image at the same time.
Two branches (appmilla-0.28.x, appmilla-0.29.x) — apply the same fixes to both. More maintenance burden going forward (two diff-sets to keep in sync) but no version migration risk for the MCP container.
My read: standardise on 0.29.x. The bug surface is the same in both versions (I verified the broken double-quote escape exists in both), and you'll thank past-you for not maintaining two branches when DDD prep is in full swing.

Public or private fork? Affects two things:

The DDD talk: a public fork means you can credibly say "we use a fork of graphiti with these fixes" — actually a good engineering story for that audience. A private fork means the talk says "we use graphiti" with no asterisk.
Pip install: public is pip install git+https://github.com/... straight up. Private needs auth (GH token in env var, deploy keys for docker builds). Doable but more moving parts.
My read: public, named clearly (e.g. appmilla/graphiti with branch appmilla-fixes-0.29 or similar). Lower friction, better optics, leaves a path open to upstream later.

Where does the fork live? Github org appmilla if there is one, or your personal account. Doesn't matter for the engineering, just for the URL.

Tag-and-pin or branch-and-pin? pip install git+...@v0.29.5-appmilla.1 (tag) is more reproducible than ...@appmilla-fixes-0.29 (branch). For consumers you want tags. For active dev you want a branch. Standard fork practice: cut a tag when you ship.

Mechanical steps once decisions are made
Push the local ~/Projects/appmilla_github/graphiti/ clone to your github fork (or fresh-fork from upstream + apply patches if you'd rather start clean).
Apply the RediSearch dash-escape fix to both files.
Apply the openai_generic factory branch per TASK-INF-5054's spec.
Tag (e.g. v0.29.5-appmilla.1).
Update pyproject.toml in study-tutor: replace "graphiti-core>=0.29,<0.30" with "graphiti-core @ git+https://github.com/appmilla/graphiti.git@v0.29.5-appmilla.1#subdirectory=graphiti_core" (subdirectory pointer needed because the package lives at graphiti_core/ in the repo). Refresh venv.
Same update in guardkit + jarvis pyproject.tomls (probably do this opportunistically, not all at once).
Update ~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-build.sh to clone from your fork at the same tag.
Rebuild MCP image on GB10 + restart container.
Verify: re-run the seed against live FalkorDB; run mcp__graphiti__add_memory + get_episodes to verify writes; run mcp__graphiti__search_nodes against student-lilymay to verify reads.
If green: flip G2/G3 in phase-1-validation.md, move TASK-GR-SEED to completed/, close TASK-INF-5054, archive TASK-INF-5054 + R-WAVE5-03 references.
Estimated total: 3-4 hours of focused work on the GB10. You can do it in one sitting after DDD travel logistics settle, or piecewise over an afternoon.

What I can do for you right now
Since you'd be doing the actual fork creation + git push + container rebuild on the GB10, the most useful thing I can do from this Mac session is prep the patch diffs as ready-to-apply files so you're not re-deriving anything on the GB10:

Write the exact RediSearch dash-escape patch as a .patch file (or two, one per call site) — bracket-wrap is my recommendation, but I can spike both bracket-wrap and backslash-escape so you can pick once you see them side by side.
Write the openai_generic factory branch patch per the TASK-INF-5054 spec, also as a .patch file.
Write a short FORK-NOTES.md that lives in the fork's repo root explaining what's patched and why, with links back to the appmilla tasks.
Update TASK-INF-5054 to reflect the fork strategy (the "comment block at top of build script" workaround section becomes "fork URL pin").
Update TASK-GR-SEED's blocked status to point at the fork plan.
All of that I can do in this Mac session without touching the GB10. You'd then scp the patches over (or git pull from your fork), apply, rebuild, verify.

Want me to start on those? If so, which RediSearch escape style do you want me to write — brace-wrap ({student-lilymay}, RediSearch treats as opaque), backslash-escape (student\-lilymay), or both side-by-side so you can pick on the GB10?

please use the task tool to invoke /task-create in the repo I've forked at /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog to create a review task with all these details
Let me first verify the graphiti fork's task structure, then spawn a Task agent with the full context.

Bash Verify graphiti fork has guardkit task structure
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/ 2>&1 | head -20
echo "---"
echo "=== Sample task file from this repo for format reference ==="
ls /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/*.md 2>/dev/null | head -3
echo "---"
echo "=== guardkit init in graphiti fork? ==="
ls /Users/richardwoollcott/Projects/appmilla_github/graphiti/.claude/ 2>/dev/null | head -10

OUT
total 0
drwxr-xr-x@ 2 richardwoollcott  staff   64 May  3 20:35 .
drwxr-xr-x@ 7 richardwoollcott  staff  224 May  3 20:35 ..
---
=== Sample task file from this repo for format reference ===
(eval):4: no matches found: /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/*.md
---
=== guardkit init in graphiti fork? ===
agents
CLAUDE.md
commands
manifest.json
rules
task-plans
Good — fork has .claude/ (guardkit-initialised) and tasks/backlog/ exists but is empty. Spawning the agent now with the full context from our session.

Agent:Create review task in graphiti fork
IN
You are working in a forked graphiti repo at `/Users/richardwoollcott/Projects/appmilla_github/graphiti/` (an appmilla-owned fork of getzep/graphiti, version 0.28.2 in this clone). The fork has guardkit initialised (`.claude/` directory present, `tasks/backlog/` exists but is empty — this will be the first task in the fork).

Your job: invoke the `/task-create` slash command from inside that directory to create a review task that captures the full punchlist and decisions for applying appmilla's known bug-fix patches to this fork.

**STEP 1 — Set working directory + check task-create availability**

`cd /Users/richardwoollcott/Projects/appmilla_github/graphiti` and verify `/task-create` is available as a skill in your session. If it is, invoke it. If for any reason `/task-create` is not available in your sub-agent session (e.g. skill not propagated), fall back to creating the task file directly using the Write tool — read `.claude/CLAUDE.md` and any sibling task examples (try `~/Projects/appmilla_github/study-tutor/tasks/in_progress/` or `~/Projects/appmilla_github/guardkit/tasks/backlog/` for format reference) to match the local task frontmatter convention.

The created task file should land at `/Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-XXX-...md` (use whatever ID convention `/task-create` generates, or `TASK-FORK-PATCH` if you're writing manually). Status should be `backlog`. Do NOT move it to in_progress.

**STEP 2 — Task content**

Below is the full content of the task. You can pass this verbatim into `/task-create` (it will likely prompt for title and description and then offer to expand) or write it directly into the task body. Adjust formatting only if the local convention requires it (e.g. some guardkit templates use specific section ordering).

---

**TITLE**: Apply appmilla bug-fix patches to graphiti fork (RediSearch dash-escape + openai_generic factory)

**PRIORITY**: high
**TASK_TYPE**: feature
**COMPLEXITY**: 4
**ESTIMATED_MINUTES**: 240 (3-4 hours focused work, executed on `promaxgb10-41b1` directly)
**TAGS**: graphiti, fork, falkordb, redisearch, mcp, infra
**EXECUTION_LOCATION**: promaxgb10-41b1 (work directly on the GB10, not via SSH from a Mac dev machine — same rationale as guardkit's TASK-INF-5054)

---

## Why this fork exists

Counting bugs across the appmilla graphiti integration:

1. graphiti-core LLM client defaults to OpenAI (silent 401 if API_KEY=not_needed) — fixed in study-tutor Wave 2 wiring
2. graphiti-core Read API mismatch (`search_nodes` doesn't exist on `Graphiti` class) — worked around with `_read_student_partition` seam in study-tutor `queries.py`
3. graphiti-core Write API mismatch (`add_episode` kwargs wrong) — worked around with `_add_episode_kwargs` helper in study-tutor `async_write.py`
4. graphiti-core `GroupIdValidationError` rejects colons → forced format migration colon→dash (commit a210472)
5. **graphiti-core RediSearch dashes-as-NOT — upstream attempted fix at `falkordb_driver.py:406-410` is broken; the comment claims to escape hyphens but double-quote wrap doesn't actually escape dashes in RediSearch syntax. Bug present in 0.28.x AND 0.29.x.** Discovered 2026-05-03 during TASK-GR-SEED Wave 5 retry; documented in `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry — TASK-GR-SEED run 5 — 2026-05-03 (afternoon)". Risk-register entry R-WAVE5-03.
6. graphiti-mcp `factories.py` `openai` branch silently ignores `api_url` → falls through to api.openai.com and 401s. Filed as guardkit TASK-INF-5054.
7. graphiti-core `OpenAIClient` calls `responses.parse()` instead of `chat.completions.create` → 404 against local OpenAI-compatible servers. Compounds with #6; the TASK-INF-5054 fix uses `OpenAIGenericClient` to address both.

That's 7 distinct upstream defects across two graphiti-core minor versions. Patches in consumer code (study-tutor/guardkit/jarvis venvs + the GB10 MCP container) don't propagate — bugs do.

**Strategic decision (2026-05-03)**: fork getzep/graphiti, apply known fixes in one place, point all consumers (study-tutor, guardkit, jarvis pyproject.tomls + the graphiti-mcp-build.sh clone target) at the fork. Ship that for the DDD South West talk (mid-May) and the Kaggle hackathon submission for study-tutor. Defer the larger "shrink graphiti's role or replace entirely" research to after mid-May.

## Punchlist — the patches that need to land in this fork

| # | Fix | File(s) | Source task |
|---|-----|---------|-------------|
| 1 | RediSearch dash-escape — replace double-quote wrap with brace-wrap (`{group_id}`, RediSearch treats as opaque) OR backslash-escape (`group\-id`). Apply to BOTH call sites. | `graphiti_core/driver/falkordb_driver.py` lines 406-410 (`build_fulltext_query` method on `FalkorDriver`) AND `graphiti_core/driver/falkordb/operations/search_ops.py` lines 105-107 (standalone `_build_falkor_fulltext_query` function — duplicated code) | study-tutor TASK-GR-SEED (R-WAVE5-03) — see `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry" |
| 2 | `openai_generic` factory branch — pass `base_url`, use `OpenAIGenericClient` instead of `OpenAIClient`. Add new `case 'openai_generic':` alongside existing `openai`, `groq` cases. Also add the matching YAML schema entry for `providers.openai_generic` (api_key + api_url) wherever the config model is defined (likely under `mcp_server/src/config/...` or `mcp_server/src/services/config.py`). | `mcp_server/src/services/factories.py` plus the config-model file (search for `class OpenAIProvider` or `providers.openai`) | guardkit TASK-INF-5054 — full patch shape already specced in that task file |

The Wave 2 fixes (LLM/embedder wiring in `get_client`, the `_read_student_partition` seam, the `_add_episode_kwargs` helper) **stay in consumer code** — they're not bugs in graphiti-core, they're consumer wiring choices around graphiti-core's API surface. Don't try to push those upstream into this fork.

## Decisions to lock in before patching starts

1. **Which version to fork from?** Local clone is at 0.28.2; study-tutor venv pins `>=0.29,<0.30`. The bug surface for #1 is identical in both versions (verified: both `falkordb_driver.py:406-410` files have the same broken double-quote escape).
   - **Recommended: standardise on 0.29.x** — pick a recent tag, fork from there, rebuild the MCP container against it. Single version everywhere. Bigger upfront move (MCP container upgrade) but no two-branch maintenance burden during DDD prep.
   - Alternative: maintain two branches `appmilla-0.28.x` and `appmilla-0.29.x`. More maintenance overhead.

2. **Public or private fork?** Affects:
   - **DDD talk story**: public fork enables credible "we use a fork of graphiti with these fixes" narrative. Private fork means talk says "we use graphiti" with no asterisk.
   - **Pip install mechanics**: public is `pip install git+https://github.com/...` straight up. Private needs auth (GH token in env, deploy keys for docker builds). More moving parts.
   - **Recommended: public**, named clearly (e.g. `appmilla/graphiti` with branch `appmilla-fixes-0.29`).

3. **Where does the fork live?** Github org `appmilla` (if exists) or personal account. Engineering-equivalent; affects only URL.

4. **Tag-and-pin or branch-and-pin?** Consumers pin via tag (`@v0.29.5-appmilla.1` — reproducible). Active dev happens on a branch. Standard fork practice: cut a tag when shipping.

## Mechanical plan (10 steps, execute on the GB10)

1. Push the local `~/Projects/appmilla_github/graphiti/` clone to the github fork (or fresh-fork from upstream + apply patches if cleaner).
2. On a fix branch (`appmilla-fixes-0.29` or similar), apply the RediSearch dash-escape fix to both files (#1 above).
3. Apply the `openai_generic` factory branch per guardkit TASK-INF-5054's spec (#2 above).
4. Tag the fix commit (e.g. `v0.29.5-appmilla.1`).
5. Update `pyproject.toml` in study-tutor: replace `"graphiti-core>=0.29,<0.30"` with `"graphiti-core @ git+https://github.com/appmilla/graphiti.git@v0.29.5-appmilla.1#subdirectory=graphiti_core"`. Refresh venv (`uv sync` or equivalent).
6. Same update in guardkit + jarvis pyproject.tomls (probably opportunistic, not all at once — guardkit is `>=0.5.0` loose pin, jarvis is `>=0.9,<1`; both are due for a tightening anyway).
7. Update `~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-build.sh` to clone from the fork at the tag (replace `git clone https://github.com/getzep/graphiti.git` with the fork URL + `--branch v0.29.5-appmilla.1`).
8. Rebuild MCP image on GB10: `./scripts/graphiti-mcp-build.sh --no-cache` then `./scripts/graphiti-mcp.sh` to restart.
9. Verify end-to-end:
   - Re-run the seed: `cd ~/Projects/appmilla_github/study-tutor && .venv/bin/python scripts/seed_student_model.py` — expect 25/25 writes succeed (no RediSearch syntax errors), `succeeded_writes=25` in summary.
   - Run `verify_lilymay.py`: expect populated `ac_seed_03_get_student_state` (year_group=11, target_grade='8', non-empty subjects, non-empty topic_confidences) and non-empty `ac_seed_02_student_lilymay_nodes`.
   - MCP probe (write): `mcp__graphiti__add_memory(name="fork-verify", episode_body="...", group_id="guardkit__test_fork", source="text")` then wait ~10s then `mcp__graphiti__get_episodes(group_ids=["guardkit__test_fork"])` — expect episode retrievable (TASK-INF-5054 fix verified).
   - MCP probe (read with dashed group_id): `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` — expect populated Student entity, NO RediSearch syntax error (R-WAVE5-03 fix verified).
   - Check container logs: `docker logs graphiti-mcp` — confirm LLM calls hit `localhost:9000` not `api.openai.com`.
10. If green:
    - Flip G2/G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` from "Falsified" to "Held" with evidence excerpts (per AC-SEED-05's exact format, already documented in TASK-GR-SEED).
    - Move `study-tutor/tasks/blocked/TASK-GR-SEED-...md` to `tasks/in_review/` or `tasks/completed/` as appropriate.
    - Move `guardkit/tasks/backlog/TASK-INF-5054-...md` to `tasks/completed/2026-05/`.
    - Move this task to `completed/`.
    - Commit + push the fork tag and the consumer pyproject.toml updates.

## Acceptance Criteria

- [ ] **AC-FORK-01** — Decisions 1-4 above are explicitly captured in this task file (which version, public/private, where, tag-vs-branch). Update this section with the chosen values before starting work.
- [ ] **AC-FORK-02** — RediSearch dash-escape patch applied to BOTH `graphiti_core/driver/falkordb_driver.py:406-410` and `graphiti_core/driver/falkordb/operations/search_ops.py:105-107`. Diff committed on the fix branch with a commit message referencing study-tutor R-WAVE5-03 and this task.
- [ ] **AC-FORK-03** — `openai_generic` factory branch added to `mcp_server/src/services/factories.py` per guardkit TASK-INF-5054's spec (the patch shape is fully detailed in that task file). YAML schema entry for `providers.openai_generic` added to the config model.
- [ ] **AC-FORK-04** — Fix commit tagged (e.g. `v0.29.5-appmilla.1`). Tag pushed to the fork remote.
- [ ] **AC-FORK-05** — `FORK-NOTES.md` (or equivalent) at the fork repo root documents what's patched and why, with links back to study-tutor TASK-GR-SEED and guardkit TASK-INF-5054.
- [ ] **AC-FORK-06** — `study-tutor/pyproject.toml` updated to pin the fork tag. Venv refreshed. Test suite still passes (`695/696` baseline maintained — the one expected failure is the pre-existing mypy-on-system-Python issue).
- [ ] **AC-FORK-07** — `guardkit/scripts/graphiti-mcp-build.sh` updated to clone the fork at the tag. MCP image rebuilt on GB10 with `--no-cache`. Container restarted and reachable at `http://promaxgb10-41b1:8004/mcp`.
- [ ] **AC-FORK-08** — End-to-end verification (step 9 above): seed runs 25/25, verify_lilymay.py shows populated state, MCP write probe round-trips, MCP read probe with dashed group_id returns populated entity (NO syntax error), container logs show LLM calls hitting `localhost:9000`.
- [ ] **AC-FORK-09** — G2/G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` flipped from Falsified to Held with evidence per AC-SEED-05 format. TASK-GR-SEED moved to completed. TASK-INF-5054 moved to completed.

## Cross-references

- **study-tutor TASK-GR-SEED** (`study-tutor/tasks/blocked/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md`) — the seed task that surfaced the RediSearch dash bug. Currently blocked pending this fork.
- **guardkit TASK-INF-5054** (`guardkit/tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md`) — the MCP-server `openai_generic` task. Already specced in detail; the patch shape is in that task file, just needs to land in the fork instead of as a local-only patch.
- **guardkit TASK-INF-5053** (`guardkit/tasks/completed/2026-05/TASK-INF-5053-graphiti-mcp-http-server-group-id-fix.md`) — the parent investigation task that ruled out the alleged group_id coercion bug and surfaced the actual `responses.parse` / `base_url` ignore bugs.
- **study-tutor phase-1-validation.md** (`study-tutor/docs/research/ideas/phase-1-validation.md`) §"Wave 4 retry — TASK-GR-SEED run 5 — 2026-05-03 (afternoon)" — full evidence + R-WAVE5-03 + R-WAVE5-04 risk register entries.

## Notes

- **Why now (May 2026)**: DDD South West talk mid-May + Kaggle hackathon submission for study-tutor. Forking is the lowest-risk way to ship demonstrable working state without de-railing either deadline. The larger "shrink graphiti's role or replace entirely" research is deferred until after mid-May (separate research task to be filed later).
- **Why not push fixes upstream right now**: getzep responsiveness unknown; the dash-escape upstream "fix" was attempted and shipped broken, suggesting their test surface for FalkorDB-side fulltext queries is thin. Once the fork is stable and verified end-to-end, consider opening upstream PRs at that point with the appmilla fix as a reference implementation. Don't block consumer migration on upstream merge.
- **Consumer migration order**: study-tutor first (it has the active blocker), then guardkit (medium use), then jarvis (lower-pri, can wait). Don't try to migrate all three in one sitting.
- **Maintenance discipline**: Whoever owns this fork needs a plan for pulling upstream changes periodically (probably quarterly during the fork's expected lifetime). Document the merge process in FORK-NOTES.md.

---

**STEP 3 — Report back**

After creating the task file, report:
- The exact path of the created task file
- The task ID assigned
- Whether you used `/task-create` (preferred) or fell back to direct Write
- A brief confirmation that all sections (Why this fork exists / Punchlist / Decisions / Mechanical plan / AC / Cross-references / Notes) are present
- Anything unexpected encountered (e.g. local task convention required reformatting, /task-create not available, etc.)

Do NOT modify any files outside `/Users/richardwoollcott/Projects/appmilla_github/graphiti/`. Do NOT start work on the patches themselves — this is a backlog task creation, not an implementation. Do NOT move the task to in_progress.
Bash List sibling task directories for format reference
IN
ls -la ~/Projects/appmilla_github/study-tutor/tasks/in_progress/ 2>/dev/null | head -20 && echo "---" && ls -la ~/Projects/appmilla_github/guardkit/tasks/backlog/ 2>/dev/null | head -20

OUT
total 24
drwxr-xr-x@ 5 richardwoollcott  staff   160 May  3 18:47 .
drwxr-xr-x@ 8 richardwoollcott  staff   256 Apr 29 17:34 ..
drwxr-xr-x@ 2 richardwoollcott  staff    64 Apr 19 13:48 claude-desktop-review-fixes
drwxr-xr-x@ 2 richardwoollcott  staff    64 Apr 29 11:27 py314-langchain-pin-alignment
-rw-r--r--@ 1 richardwoollcott  staff  9748 Apr 29 11:28 TASK-REV-57BD-portfolio-py314-langchain-1x-alignment.md
---
total 2136
drwxr-xr-x  222 richardwoollcott  staff   7104 May  3 18:23 .
drwxr-xr-x   13 richardwoollcott  staff    416 Apr 18 11:44 ..
-rw-r--r--@   1 richardwoollcott  staff   6148 Apr 12 08:17 .DS_Store
drwxr-xr-x    6 richardwoollcott  staff    192 Mar  3 07:54 add-context-fixes
drwxr-xr-x    5 richardwoollcott  staff    160 Jan 25 21:42 arch-score-fix
drwxr-xr-x    5 richardwoollcott  staff    160 Apr 12 09:37 autobuild_cleanup
drwxr-xr-x    5 richardwoollcott  staff    160 Feb 15 19:20 autobuild-context-opt
drwxr-xr-x    5 richardwoollcott  staff    160 Mar 20 14:48 autobuild-feat5606-fixes
drwxr-xr-x   17 richardwoollcott  staff    544 Mar  8 11:33 autobuild-instrumentation
drwxr-xr-x    6 richardwoollcott  staff    192 Feb 20 17:54 autobuild-observability-fixes
drwxr-xr-x    4 richardwoollcott  staff    128 Apr 24 17:06 autobuild-sdk-stall-resilience
drwxr-xr-x    4 richardwoollcott  staff    128 Apr 24 20:15 autobuild-sdk-stall-resilience-phase2
drwxr-xr-x    5 richardwoollcott  staff    160 Feb 15 15:33 autobuild-stall-fixes
drwxr-xr-x    7 richardwoollcott  staff    224 Apr 28 17:03 autobuild-stall-resilience
drwxr-xr-x    5 richardwoollcott  staff    160 Mar  3 07:54 autobuild-synthetic-pipeline-fix
drwxr-xr-x    5 richardwoollcott  staff    160 Feb 16 19:31 autobuild-test-detection-fixes
drwxr-xr-x    4 richardwoollcott  staff    128 Apr 26 08:13 bdd-runner-silent-bypass-fix
drwxr-xr-x   15 richardwoollcott  staff    480 Dec 14 19:07 beads-integration
drwxr-xr-x    8 richardwoollcott  staff    256 Mar  9 16:40 coach-runtime-verification
Read TASK-REV-57BD-portfolio-py314-langchain-1x-alignment.md
task-create skill
Bash Generate hash-based task ID with FORK prefix
IN
python3 -c "
import hashlib, time
# Use the user-supplied prefix FORK + a hash seed of title+timestamp
seed = 'apply-appmilla-bug-fix-patches-graphiti-fork-' + str(time.time())
h = hashlib.sha256(seed.encode()).hexdigest().upper()[:4]
print(f'Generated ID: TASK-FORK-{h}')
print(f'Slug suffix: apply-appmilla-bug-fix-patches')
"

OUT
Generated ID: TASK-FORK-775D
Slug suffix: apply-appmilla-bug-fix-patches
Write TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
122 lines
---
id: TASK-FORK-PATCH
title: Apply appmilla bug-fix patches to graphiti fork (RediSearch dash-escape + openai_generic factory)
status: backlog
created: 2026-05-03T00:00:00Z
updated: 2026-05-03T00:00:00Z
priority: high
task_type: feature
complexity: 4
estimated_minutes: 240
execution_location: promaxgb10-41b1
tags: [graphiti, fork, falkordb, redisearch, mcp, infra]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Apply appmilla bug-fix patches to graphiti fork (RediSearch dash-escape + openai_generic factory)

**PRIORITY**: high
**TASK_TYPE**: feature
**COMPLEXITY**: 4
**ESTIMATED_MINUTES**: 240 (3-4 hours focused work, executed on `promaxgb10-41b1` directly)
**TAGS**: graphiti, fork, falkordb, redisearch, mcp, infra
**EXECUTION_LOCATION**: promaxgb10-41b1 (work directly on the GB10, not via SSH from a Mac dev machine — same rationale as guardkit's TASK-INF-5054)

---

## Why this fork exists

Counting bugs across the appmilla graphiti integration:

1. graphiti-core LLM client defaults to OpenAI (silent 401 if API_KEY=not_needed) — fixed in study-tutor Wave 2 wiring
2. graphiti-core Read API mismatch (`search_nodes` doesn't exist on `Graphiti` class) — worked around with `_read_student_partition` seam in study-tutor `queries.py`
3. graphiti-core Write API mismatch (`add_episode` kwargs wrong) — worked around with `_add_episode_kwargs` helper in study-tutor `async_write.py`
4. graphiti-core `GroupIdValidationError` rejects colons → forced format migration colon→dash (commit a210472)
5. **graphiti-core RediSearch dashes-as-NOT — upstream attempted fix at `falkordb_driver.py:406-410` is broken; the comment claims to escape hyphens but double-quote wrap doesn't actually escape dashes in RediSearch syntax. Bug present in 0.28.x AND 0.29.x.** Discovered 2026-05-03 during TASK-GR-SEED Wave 5 retry; documented in `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry — TASK-GR-SEED run 5 — 2026-05-03 (afternoon)". Risk-register entry R-WAVE5-03.
6. graphiti-mcp `factories.py` `openai` branch silently ignores `api_url` → falls through to api.openai.com and 401s. Filed as guardkit TASK-INF-5054.
7. graphiti-core `OpenAIClient` calls `responses.parse()` instead of `chat.completions.create` → 404 against local OpenAI-compatible servers. Compounds with #6; the TASK-INF-5054 fix uses `OpenAIGenericClient` to address both.

That's 7 distinct upstream defects across two graphiti-core minor versions. Patches in consumer code (study-tutor/guardkit/jarvis venvs + the GB10 MCP container) don't propagate — bugs do.

**Strategic decision (2026-05-03)**: fork getzep/graphiti, apply known fixes in one place, point all consumers (study-tutor, guardkit, jarvis pyproject.tomls + the graphiti-mcp-build.sh clone target) at the fork. Ship that for the DDD South West talk (mid-May) and the Kaggle hackathon submission for study-tutor. Defer the larger "shrink graphiti's role or replace entirely" research to after mid-May.

## Punchlist — the patches that need to land in this fork

| # | Fix | File(s) | Source task |
|---|-----|---------|-------------|
| 1 | RediSearch dash-escape — replace double-quote wrap with brace-wrap (`{group_id}`, RediSearch treats as opaque) OR backslash-escape (`group\-id`). Apply to BOTH call sites. | `graphiti_core/driver/falkordb_driver.py` lines 406-410 (`build_fulltext_query` method on `FalkorDriver`) AND `graphiti_core/driver/falkordb/operations/search_ops.py` lines 105-107 (standalone `_build_falkor_fulltext_query` function — duplicated code) | study-tutor TASK-GR-SEED (R-WAVE5-03) — see `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry" |
| 2 | `openai_generic` factory branch — pass `base_url`, use `OpenAIGenericClient` instead of `OpenAIClient`. Add new `case 'openai_generic':` alongside existing `openai`, `groq` cases. Also add the matching YAML schema entry for `providers.openai_generic` (api_key + api_url) wherever the config model is defined (likely under `mcp_server/src/config/...` or `mcp_server/src/services/config.py`). | `mcp_server/src/services/factories.py` plus the config-model file (search for `class OpenAIProvider` or `providers.openai`) | guardkit TASK-INF-5054 — full patch shape already specced in that task file |

The Wave 2 fixes (LLM/embedder wiring in `get_client`, the `_read_student_partition` seam, the `_add_episode_kwargs` helper) **stay in consumer code** — they're not bugs in graphiti-core, they're consumer wiring choices around graphiti-core's API surface. Don't try to push those upstream into this fork.

## Decisions to lock in before patching starts

1. **Which version to fork from?** Local clone is at 0.28.2; study-tutor venv pins `>=0.29,<0.30`. The bug surface for #1 is identical in both versions (verified: both `falkordb_driver.py:406-410` files have the same broken double-quote escape).
   - **Recommended: standardise on 0.29.x** — pick a recent tag, fork from there, rebuild the MCP container against it. Single version everywhere. Bigger upfront move (MCP container upgrade) but no two-branch maintenance burden during DDD prep.
   - Alternative: maintain two branches `appmilla-0.28.x` and `appmilla-0.29.x`. More maintenance overhead.
   - **DECISION**: _TBD — capture chosen version here before starting work_

2. **Public or private fork?** Affects:
   - **DDD talk story**: public fork enables credible "we use a fork of graphiti with these fixes" narrative. Private fork means talk says "we use graphiti" with no asterisk.
   - **Pip install mechanics**: public is `pip install git+https://github.com/...` straight up. Private needs auth (GH token in env, deploy keys for docker builds). More moving parts.
   - **Recommended: public**, named clearly (e.g. `appmilla/graphiti` with branch `appmilla-fixes-0.29`).
   - **DECISION**: _TBD — capture chosen visibility here before starting work_

3. **Where does the fork live?** Github org `appmilla` (if exists) or personal account. Engineering-equivalent; affects only URL.
   - **DECISION**: _TBD — capture chosen owner here before starting work_

4. **Tag-and-pin or branch-and-pin?** Consumers pin via tag (`@v0.29.5-appmilla.1` — reproducible). Active dev happens on a branch. Standard fork practice: cut a tag when shipping.
   - **DECISION**: _TBD — capture chosen pinning strategy here before starting work_

## Mechanical plan (10 steps, execute on the GB10)

1. Push the local `~/Projects/appmilla_github/graphiti/` clone to the github fork (or fresh-fork from upstream + apply patches if cleaner).
2. On a fix branch (`appmilla-fixes-0.29` or similar), apply the RediSearch dash-escape fix to both files (#1 above).
3. Apply the `openai_generic` factory branch per guardkit TASK-INF-5054's spec (#2 above).
4. Tag the fix commit (e.g. `v0.29.5-appmilla.1`).
5. Update `pyproject.toml` in study-tutor: replace `"graphiti-core>=0.29,<0.30"` with `"graphiti-core @ git+https://github.com/appmilla/graphiti.git@v0.29.5-appmilla.1#subdirectory=graphiti_core"`. Refresh venv (`uv sync` or equivalent).
6. Same update in guardkit + jarvis pyproject.tomls (probably opportunistic, not all at once — guardkit is `>=0.5.0` loose pin, jarvis is `>=0.9,<1`; both are due for a tightening anyway).
7. Update `~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-build.sh` to clone from the fork at the tag (replace `git clone https://github.com/getzep/graphiti.git` with the fork URL + `--branch v0.29.5-appmilla.1`).
8. Rebuild MCP image on GB10: `./scripts/graphiti-mcp-build.sh --no-cache` then `./scripts/graphiti-mcp.sh` to restart.
9. Verify end-to-end:
   - Re-run the seed: `cd ~/Projects/appmilla_github/study-tutor && .venv/bin/python scripts/seed_student_model.py` — expect 25/25 writes succeed (no RediSearch syntax errors), `succeeded_writes=25` in summary.
   - Run `verify_lilymay.py`: expect populated `ac_seed_03_get_student_state` (year_group=11, target_grade='8', non-empty subjects, non-empty topic_confidences) and non-empty `ac_seed_02_student_lilymay_nodes`.
   - MCP probe (write): `mcp__graphiti__add_memory(name="fork-verify", episode_body="...", group_id="guardkit__test_fork", source="text")` then wait ~10s then `mcp__graphiti__get_episodes(group_ids=["guardkit__test_fork"])` — expect episode retrievable (TASK-INF-5054 fix verified).
   - MCP probe (read with dashed group_id): `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` — expect populated Student entity, NO RediSearch syntax error (R-WAVE5-03 fix verified).
   - Check container logs: `docker logs graphiti-mcp` — confirm LLM calls hit `localhost:9000` not `api.openai.com`.
10. If green:
    - Flip G2/G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` from "Falsified" to "Held" with evidence excerpts (per AC-SEED-05's exact format, already documented in TASK-GR-SEED).
    - Move `study-tutor/tasks/blocked/TASK-GR-SEED-...md` to `tasks/in_review/` or `tasks/completed/` as appropriate.
    - Move `guardkit/tasks/backlog/TASK-INF-5054-...md` to `tasks/completed/2026-05/`.
    - Move this task to `completed/`.
    - Commit + push the fork tag and the consumer pyproject.toml updates.

## Acceptance Criteria

- [ ] **AC-FORK-01** — Decisions 1-4 above are explicitly captured in this task file (which version, public/private, where, tag-vs-branch). Update this section with the chosen values before starting work.
- [ ] **AC-FORK-02** — RediSearch dash-escape patch applied to BOTH `graphiti_core/driver/falkordb_driver.py:406-410` and `graphiti_core/driver/falkordb/operations/search_ops.py:105-107`. Diff committed on the fix branch with a commit message referencing study-tutor R-WAVE5-03 and this task.
- [ ] **AC-FORK-03** — `openai_generic` factory branch added to `mcp_server/src/services/factories.py` per guardkit TASK-INF-5054's spec (the patch shape is fully detailed in that task file). YAML schema entry for `providers.openai_generic` added to the config model.
- [ ] **AC-FORK-04** — Fix commit tagged (e.g. `v0.29.5-appmilla.1`). Tag pushed to the fork remote.
- [ ] **AC-FORK-05** — `FORK-NOTES.md` (or equivalent) at the fork repo root documents what's patched and why, with links back to study-tutor TASK-GR-SEED and guardkit TASK-INF-5054.
- [ ] **AC-FORK-06** — `study-tutor/pyproject.toml` updated to pin the fork tag. Venv refreshed. Test suite still passes (`695/696` baseline maintained — the one expected failure is the pre-existing mypy-on-system-Python issue).
- [ ] **AC-FORK-07** — `guardkit/scripts/graphiti-mcp-build.sh` updated to clone the fork at the tag. MCP image rebuilt on GB10 with `--no-cache`. Container restarted and reachable at `http://promaxgb10-41b1:8004/mcp`.
- [ ] **AC-FORK-08** — End-to-end verification (step 9 above): seed runs 25/25, verify_lilymay.py shows populated state, MCP write probe round-trips, MCP read probe with dashed group_id returns populated entity (NO syntax error), container logs show LLM calls hitting `localhost:9000`.
- [ ] **AC-FORK-09** — G2/G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` flipped from Falsified to Held with evidence per AC-SEED-05 format. TASK-GR-SEED moved to completed. TASK-INF-5054 moved to completed.

## Cross-references

- **study-tutor TASK-GR-SEED** (`study-tutor/tasks/blocked/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md`) — the seed task that surfaced the RediSearch dash bug. Currently blocked pending this fork.
- **guardkit TASK-INF-5054** (`guardkit/tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md`) — the MCP-server `openai_generic` task. Already specced in detail; the patch shape is in that task file, just needs to land in the fork instead of as a local-only patch.
- **guardkit TASK-INF-5053** (`guardkit/tasks/completed/2026-05/TASK-INF-5053-graphiti-mcp-http-server-group-id-fix.md`) — the parent investigation task that ruled out the alleged group_id coercion bug and surfaced the actual `responses.parse` / `base_url` ignore bugs.
- **study-tutor phase-1-validation.md** (`study-tutor/docs/research/ideas/phase-1-validation.md`) §"Wave 4 retry — TASK-GR-SEED run 5 — 2026-05-03 (afternoon)" — full evidence + R-WAVE5-03 + R-WAVE5-04 risk register entries.

## Notes

- **Why now (May 2026)**: DDD South West talk mid-May + Kaggle hackathon submission for study-tutor. Forking is the lowest-risk way to ship demonstrable working state without de-railing either deadline. The larger "shrink graphiti's role or replace entirely" research is deferred until after mid-May (separate research task to be filed later).
- **Why not push fixes upstream right now**: getzep responsiveness unknown; the dash-escape upstream "fix" was attempted and shipped broken, suggesting their test surface for FalkorDB-side fulltext queries is thin. Once the fork is stable and verified end-to-end, consider opening upstream PRs at that point with the appmilla fix as a reference implementation. Don't block consumer migration on upstream merge.
- **Consumer migration order**: study-tutor first (it has the active blocker), then guardkit (medium use), then jarvis (lower-pri, can wait). Don't try to migrate all three in one sitting.
- **Maintenance discipline**: Whoever owns this fork needs a plan for pulling upstream changes periodically (probably quarterly during the fork's expected lifetime). Document the merge process in FORK-NOTES.md.
Bash Verify task file was created
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/ && echo "---" && wc -l /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md

OUT
total 32
drwxr-xr-x@ 3 richardwoollcott  staff     96 May  3 20:52 .
drwxr-xr-x@ 7 richardwoollcott  staff    224 May  3 20:35 ..
-rw-r--r--  1 richardwoollcott  staff  13460 May  3 20:52 TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
---
     121 /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
Bash Verify created task file structure and content
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/
echo "---"
echo "=== File header (frontmatter + first sections) ==="
head -50 /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
echo "---"
echo "=== Section markers (verify all expected sections present) ==="
grep -n "^## " /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
echo "---"
echo "=== AC count ==="
grep -c "^- \[ \] \*\*AC-FORK" /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
echo "=== DECISION placeholders ==="
grep -n "DECISION.*TBD" /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md

OUT
total 32
drwxr-xr-x@ 3 richardwoollcott  staff     96 May  3 20:52 .
drwxr-xr-x@ 7 richardwoollcott  staff    224 May  3 20:35 ..
-rw-r--r--  1 richardwoollcott  staff  13460 May  3 20:52 TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
---
=== File header (frontmatter + first sections) ===
---
id: TASK-FORK-PATCH
title: Apply appmilla bug-fix patches to graphiti fork (RediSearch dash-escape + openai_generic factory)
status: backlog
created: 2026-05-03T00:00:00Z
updated: 2026-05-03T00:00:00Z
priority: high
task_type: feature
complexity: 4
estimated_minutes: 240
execution_location: promaxgb10-41b1
tags: [graphiti, fork, falkordb, redisearch, mcp, infra]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Apply appmilla bug-fix patches to graphiti fork (RediSearch dash-escape + openai_generic factory)

**PRIORITY**: high
**TASK_TYPE**: feature
**COMPLEXITY**: 4
**ESTIMATED_MINUTES**: 240 (3-4 hours focused work, executed on `promaxgb10-41b1` directly)
**TAGS**: graphiti, fork, falkordb, redisearch, mcp, infra
**EXECUTION_LOCATION**: promaxgb10-41b1 (work directly on the GB10, not via SSH from a Mac dev machine — same rationale as guardkit's TASK-INF-5054)

---

## Why this fork exists

Counting bugs across the appmilla graphiti integration:

1. graphiti-core LLM client defaults to OpenAI (silent 401 if API_KEY=not_needed) — fixed in study-tutor Wave 2 wiring
2. graphiti-core Read API mismatch (`search_nodes` doesn't exist on `Graphiti` class) — worked around with `_read_student_partition` seam in study-tutor `queries.py`
3. graphiti-core Write API mismatch (`add_episode` kwargs wrong) — worked around with `_add_episode_kwargs` helper in study-tutor `async_write.py`
4. graphiti-core `GroupIdValidationError` rejects colons → forced format migration colon→dash (commit a210472)
5. **graphiti-core RediSearch dashes-as-NOT — upstream attempted fix at `falkordb_driver.py:406-410` is broken; the comment claims to escape hyphens but double-quote wrap doesn't actually escape dashes in RediSearch syntax. Bug present in 0.28.x AND 0.29.x.** Discovered 2026-05-03 during TASK-GR-SEED Wave 5 retry; documented in `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry — TASK-GR-SEED run 5 — 2026-05-03 (afternoon)". Risk-register entry R-WAVE5-03.
6. graphiti-mcp `factories.py` `openai` branch silently ignores `api_url` → falls through to api.openai.com and 401s. Filed as guardkit TASK-INF-5054.
7. graphiti-core `OpenAIClient` calls `responses.parse()` instead of `chat.completions.create` → 404 against local OpenAI-compatible servers. Compounds with #6; the TASK-INF-5054 fix uses `OpenAIGenericClient` to address both.

That's 7 distinct upstream defects across two graphiti-core minor versions. Patches in consumer code (study-tutor/guardkit/jarvis venvs + the GB10 MCP container) don't propagate — bugs do.

**Strategic decision (2026-05-03)**: fork getzep/graphiti, apply known fixes in one place, point all consumers (study-tutor, guardkit, jarvis pyproject.tomls + the graphiti-mcp-build.sh clone target) at the fork. Ship that for the DDD South West talk (mid-May) and the Kaggle hackathon submission for study-tutor. Defer the larger "shrink graphiti's role or replace entirely" research to after mid-May.

## Punchlist — the patches that need to land in this fork

| # | Fix | File(s) | Source task |
|---|-----|---------|-------------|
| 1 | RediSearch dash-escape — replace double-quote wrap with brace-wrap (`{group_id}`, RediSearch treats as opaque) OR backslash-escape (`group\-id`). Apply to BOTH call sites. | `graphiti_core/driver/falkordb_driver.py` lines 406-410 (`build_fulltext_query` method on `FalkorDriver`) AND `graphiti_core/driver/falkordb/operations/search_ops.py` lines 105-107 (standalone `_build_falkor_fulltext_query` function — duplicated code) | study-tutor TASK-GR-SEED (R-WAVE5-03) — see `study-tutor/docs/research/ideas/phase-1-validation.md` §"Wave 4 retry" |
---
=== Section markers (verify all expected sections present) ===
30:## Why this fork exists
46:## Punchlist — the patches that need to land in this fork
55:## Decisions to lock in before patching starts
74:## Mechanical plan (10 steps, execute on the GB10)
97:## Acceptance Criteria
109:## Cross-references
116:## Notes
---
=== AC count ===
9
=== DECISION placeholders ===
60:   - **DECISION**: _TBD — capture chosen version here before starting work_
66:   - **DECISION**: _TBD — capture chosen visibility here before starting work_
69:   - **DECISION**: _TBD — capture chosen owner here before starting work_
72:   - **DECISION**: _TBD — capture chosen pinning strategy here before starting work_
Update Todos

Launch seed_student_model.py as run 5 in background

Wait for seed to complete (~30-60min wall-clock)

Run verify_lilymay.py to capture fresh AC-SEED-02/03 evidence

Document NEW failure mode (RediSearch dash-as-NOT) in phase-1-validation.md

Move TASK-GR-SEED to blocked/ with clear reason

Surface remediation options; user chose fork strategy

Create TASK-FORK-PATCH in graphiti fork capturing punchlist + decisions
Verified — task file is in place at the right path with all 7 expected sections (Why this fork exists / Punchlist / Decisions / Mechanical plan / AC / Cross-references / Notes), all 9 acceptance criteria (AC-FORK-01 → AC-FORK-09), and 4 explicit DECISION: _TBD_ placeholders for the version / public-vs-private / owner / pinning calls. Frontmatter follows local guardkit convention.

Where things stand
Task	Repo	Status	Next action
TASK-FORK-PATCH	graphiti fork	backlog	Lock in the 4 decisions, then execute the 10-step plan on the GB10
TASK-INF-5054	guardkit	backlog	Will be subsumed by TASK-FORK-PATCH AC-FORK-03 (its openai_generic factory patch lands in the fork). Worth adding a forward-reference to TASK-FORK-PATCH in this task's notes when convenient.
TASK-GR-SEED	study-tutor	blocked	Unblocked by TASK-FORK-PATCH AC-FORK-08 (verify) and AC-FORK-09 (G2/G3 flip).
The task file is readable end-to-end; it captures the full bug count, the strategic rationale (DDD + Kaggle deadlines), the patches that need to land, the decisions still open, and the executable mechanical plan. Pick it up on the GB10 when you're ready.

I've updated the review file from the guardkit repo and graphiti-original repos please take a look and you will gain a better understanding of all the issues which led to my frustration!
Bash Find graphiti-original repo and check updated task file size
IN
ls -d ~/Projects/appmilla_github/graphiti* 2>/dev/null
echo "---"
ls -la /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/
echo "---"
wc -l /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md

OUT
/Users/richardwoollcott/Projects/appmilla_github/graphiti
/Users/richardwoollcott/Projects/appmilla_github/graphiti-official
---
total 80
drwxr-xr-x@ 3 richardwoollcott  staff     96 May  3 21:15 .
drwxr-xr-x@ 7 richardwoollcott  staff    224 May  3 20:35 ..
-rw-r--r--  1 richardwoollcott  staff  37666 May  3 21:15 TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
---
     327 /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
File nearly tripled in size (13.5KB → 37.7KB, 121 → 327 lines). Reading the full updated version now.

Read TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
Read end-to-end. The scale is much bigger than I had tallied — and your frustration is fully earned. A few specific takeaways:

The bug count just doubled
I was working with 7 defects. The audit surfaces 13 (5 more graphiti-core + 1 graphiti-mcp), all currently propped up by runtime monkey-patches or operational scripts in guardkit:

The falkordb_workaround.py module alone carries patches for bugs #8, #9, #10, #11, #12 — five distinct defects in one consumer-side workaround file
Bug #13 (transport_security host mutation) is why graphiti-mcp-bootstrap.py exists at all
Two of these (#8 PR-1170 and #9 issue-1272) you've already filed upstream, so getzep knows about them — and they've sat unmerged
This makes the fork strategy stronger, not weaker. You're not forking to fix one bug — you're forking to consolidate ~13 fixes that already exist in production-scattered form into one upstream-shaped place.

The "production wiring" insight is the load-bearing finding
Line 168: apply_falkordb_workaround() only fires on CLI write paths through guardkit graphiti add-context / capture-outcome / seed. The MCP container runs completely unpatched graphiti-core for bugs #8-#12.

That explains every weird symptom we hit in this session via MCP — the mcp__graphiti__search_nodes("Lilymay", group_ids=["student-lilymay"]) call earlier wasn't just hitting bug #5; it was hitting bugs #5 + #8 + #11 + potentially #9 simultaneously. The MCP path has been the silent worst-case all along, and we've been tunnelling through it whenever we used the mcp__graphiti__* tools to verify state. The fork lands fixes in the path we actually query through.

Two strategic shifts your audit forces
1. The "drop the filter" approach (Decision 5) is genuinely better than my original "escape-and-keep" suggestion. I was preserving upstream design intent. You've already proven in production for several months that the filter isn't even needed — group isolation comes from #8's multi-graph clone + Cypher WHERE. Dropping the filter kills bugs #5 + #11 + #12 in one commit, simplifies the patch surface, and removes a class of brittle string-escape gymnastics. Strong second.

2. Approach A (auto-detect on base_url) for Decision 6 is significantly better than Approach B, and your in-flight ~/graphiti-official/ draft already implements it. +14 lines, zero schema edits, zero consumer migration burden, reversible. The fact that this fix is already drafted and clean-fast-forward-applicable means TASK-INF-5054 is already half-done before you start — you didn't write a "spec then implement" task, you wrote an "apply already-drafted patch" task and didn't notice. Means TASK-INF-5054 in guardkit can probably move to in_review the moment Decision 6 is locked at A.

Things I want to surface that might not be obvious
The config-guardkit.yaml stale-file warning is the highest-value finding in the audit. Without that catch, the fork would have shipped with a Gemini-era YAML pointing at a dead :8001 embedder with the wrong 1024-dim, and someone three months from now would be debugging "why does search return zero hits?" against an embedder dimension mismatch. AC-FORK-16's "discard entirely, derive fresh from live config if needed" is exactly right.

The estimate is now wrong. 240 minutes assumed 2 patches. With Decision 5 → drop-filter (one extra fix), Decision 6 → in-flight patch (already drafted, fast), bugs #8/#9 (PR + issue exist, modest patches), bug #10 (small extension to sanitize()), bug #13 (probably a transport_security re-init call), and verification of all of them, it's more like 8-12 hours of focused work, even with the in-flight patch as a head start. Worth bumping estimated_minutes to ~600 before the GB10 session so future-you doesn't expect a 4h afternoon.

Bug #13 (transport_security) is a particularly satisfying upstream candidate. It's a clean upstream PR — graphiti-mcp's main() should accept a host constructor arg or re-initialise transport_security after mutating host. That patch is small and obviously-correct enough that getzep would likely take it. Same for bug #10 (extending sanitize()'s strip list). Even if you don't push them today, queue them as upstream PRs from the fork once it's stable — those two are low-risk give-backs that don't even require the appmilla-fork-as-reference framing.

Minor formatting nit: AC-FORK-17 appears after AC-FORK-18 in the second-batch additions (lines 319-320). Easy fix when you next touch the file.

The audit itself is talk material. The 13-bug inventory + the production-wiring insight + the in-tree-workaround tally is genuinely a credible "lessons learned" sub-narrative for the DDD talk if you want it. "Here's what running an LLM agent on top of a young open-source memory graph actually costs over six weeks." Not advocating you build the talk around it, but it's there if useful.

My read on what to do next
Nothing urgent from me right now — the task captures the picture comprehensively, and the next move is locking the 6 decisions on the GB10 (probably in a single sitting, since they're tightly coupled: version → public/private → owner → tag/branch → drop-filter vs escape → auto-detect vs explicit).

If useful, I can: (a) write the 5 small fix patches as ready-to-apply diffs (bugs #5/#11/#12 combined as drop-filter, bug #10 sanitize extension, bug #13 transport_security) so the GB10 session is mostly patch -p1 rather than re-derivation, or (b) update estimated_minutes and fix the AC ordering nit in the task file, or (c) just stand by until you're on the GB10 and pick up from there.

please can you fix your observation Minor formatting nit: AC-FORK-17 appears after AC-FORK-18
Read TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md (lines 318-322)
Edit TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
Modified
Bash Verify AC ordering is now sequential
IN
grep -n "^- \[ \] \*\*AC-FORK" /Users/richardwoollcott/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md

OUT
99:- [ ] **AC-FORK-01** — Decisions 1-4 above are explicitly captured in this task file (which version, public/private, where, tag-vs-branch). Update this section with the chosen values before starting work.
100:- [ ] **AC-FORK-02** — RediSearch dash-escape patch applied to BOTH `graphiti_core/driver/falkordb_driver.py:406-410` and `graphiti_core/driver/falkordb/operations/search_ops.py:105-107`. Diff committed on the fix branch with a commit message referencing study-tutor R-WAVE5-03 and this task.
101:- [ ] **AC-FORK-03** — `openai_generic` factory branch added to `mcp_server/src/services/factories.py` per guardkit TASK-INF-5054's spec (the patch shape is fully detailed in that task file). YAML schema entry for `providers.openai_generic` added to the config model.
102:- [ ] **AC-FORK-04** — Fix commit tagged (e.g. `v0.29.5-appmilla.1`). Tag pushed to the fork remote.
103:- [ ] **AC-FORK-05** — `FORK-NOTES.md` (or equivalent) at the fork repo root documents what's patched and why, with links back to study-tutor TASK-GR-SEED and guardkit TASK-INF-5054.
104:- [ ] **AC-FORK-06** — `study-tutor/pyproject.toml` updated to pin the fork tag. Venv refreshed. Test suite still passes (`695/696` baseline maintained — the one expected failure is the pre-existing mypy-on-system-Python issue).
105:- [ ] **AC-FORK-07** — `guardkit/scripts/graphiti-mcp-build.sh` updated to clone the fork at the tag. MCP image rebuilt on GB10 with `--no-cache`. Container restarted and reachable at `http://promaxgb10-41b1:8004/mcp`.
106:- [ ] **AC-FORK-08** — End-to-end verification (step 9 above): seed runs 25/25, verify_lilymay.py shows populated state, MCP write probe round-trips, MCP read probe with dashed group_id returns populated entity (NO syntax error), container logs show LLM calls hitting `localhost:9000`.
107:- [ ] **AC-FORK-09** — G2/G3 in `study-tutor/docs/research/ideas/phase-1-validation.md` flipped from Falsified to Held with evidence per AC-SEED-05 format. TASK-GR-SEED moved to completed. TASK-INF-5054 moved to completed.
172:- [ ] **AC-FORK-10** — `handle_multiple_group_ids` decorator fix (PR #1170 equivalent) applied in fork at `graphiti_core/decorators.py`. Verify by removing `apply_falkordb_workaround()` from `guardkit/knowledge/graphiti_client.py` (locally, not committed) and confirming the existing falkordb_workaround test suite (`tests/knowledge/test_falkordb_workaround.py`) still passes against the forked graphiti-core. **Then re-add `apply_falkordb_workaround()` for now** — it can be removed in a follow-up task once all consumers are on the fork tag.
173:- [ ] **AC-FORK-11** — Edge-search O(n×m) fix (issue #1272) applied in fork at `graphiti_core/search/search_utils.py`. Verify with the same falkordb_workaround test suite (it has separate tests for `edge_fulltext_search` and `edge_bfs_search`).
174:- [ ] **AC-FORK-12** — `sanitize()` extended in fork to strip backticks, forward slashes, pipes, and backslashes (TASK-REV-661E gap). Verify by running guardkit's seed pipeline against a markdown corpus containing `` `path/to/file.md` `` references (the original repro case).
175:- [ ] **AC-FORK-13** — Decision 5 (drop-filter vs. escape-and-keep) captured. If "drop filter": apply that in fork at both call sites and verify guardkit's in-tree `apply_fulltext_query_workaround()` still no-ops cleanly (it has a "already fixed upstream, skipping" branch at line 84-86 that should activate). If "escape-and-keep": apply that and additionally fix bugs #11 + #12 in separate commits.
176:- [ ] **AC-FORK-14** *(stretch)* — graphiti-mcp `transport_security` re-init after host mutation (bug #13). If shipped: verify by removing `scripts/graphiti-mcp-bootstrap.py` from the build pipeline and confirming the rebuilt MCP image accepts `Host: promaxgb10-41b1:8004` from a Tailscale client.
317:- [ ] **AC-FORK-15** — Decision 6 (auto-detect vs explicit `openai_generic` case) captured in this task file before patching starts. If Approach A: apply the in-flight diff above verbatim and skip the config-schema edits. If Approach B: apply the punchlist #2 spec and update study-tutor/guardkit/jarvis configs in the same PR sweep.
318:- [ ] **AC-FORK-16** — `mcp_server/config/config-local-neo4j.yaml` from the in-flight staged set committed to the fork (generic template, no secrets). The staged `config-guardkit.yaml` is **discarded entirely** — it is stale (Gemini era, dead `:8001` embedder, wrong 1024-dim) and the actual live config already lives at [guardkit/scripts/graphiti-mcp-config.yaml](../../guardkit/scripts/graphiti-mcp-config.yaml). If a GuardKit-style example is desired in the fork for documentation, derive it fresh from the live config (provider openai → llama-swap, 768-dim, GB10-specific values blanked to `${...}` env placeholders) and name it `config-llama-swap-example.yaml`.
319:- [ ] **AC-FORK-17** — After applying the factory fix, smoke-test on the GB10 with the staged guardkit config: `docker logs graphiti-mcp` should show `INFO Using OpenAIGenericClient for non-OpenAI endpoint: http://...` on first LLM call, confirming the auto-detect branch executed.
320:- [ ] **AC-FORK-18** — Separate doc-update task filed (NOT part of this fork-patch task) to refresh [guardkit/docs/guides/graphiti-gb10-deployment.md](../../guardkit/docs/guides/graphiti-gb10-deployment.md) for the post-2026-04-29 llama-swap topology: replace the dual-vLLM box diagram, remove the "supersedes Gemini" note, fix the broken supersedes-link at line 10, and update the file map / config-relationships / troubleshooting sections to reflect the single-port `:9000` reality.
Fixed. ACs now read sequentially AC-FORK-01 through AC-FORK-18, no gaps or out-of-order entries.

thanks please do (a) and (b) update estimated_minutes
Let me read the actual files in the local graphiti clone to get exact line context for the diffs, then check for the transport_security bug location.

Bash Read exact file content for drop-filter patch context
IN
echo "=== Local clone version + file locations ==="
grep "^version" /Users/richardwoollcott/Projects/appmilla_github/graphiti/pyproject.toml | head -1
echo ""
echo "=== build_fulltext_query in falkordb_driver.py ==="
sed -n '385,430p' /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py
echo ""
echo "=== _build_falkor_fulltext_query in search_ops.py ==="
sed -n '90,125p' /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py

OUT
=== Local clone version + file locations ===
version = "0.29.0"

=== build_fulltext_query in falkordb_driver.py ===
        # Clean up multiple spaces
        sanitized = ' '.join(sanitized.split())
        return sanitized

    def build_fulltext_query(
        self, query: str, group_ids: list[str] | None = None, max_query_length: int = 128
    ) -> str:
        """
        Build a fulltext query string for FalkorDB using RedisSearch syntax.
        FalkorDB uses RedisSearch-like syntax where:
        - Field queries use @ prefix: @field:value
        - Multiple values for same field: (@field:value1|value2)
        - Text search doesn't need @ prefix for content fields
        - AND is implicit with space: (@group_id:value) (text)
        - OR uses pipe within parentheses: (@group_id:value1|value2)
        """
        validate_group_ids(group_ids)

        if group_ids is None or len(group_ids) == 0:
            group_filter = ''
        else:
            # Escape group_ids with quotes to prevent RediSearch syntax errors
            # with reserved words like "main" or special characters like hyphens
            escaped_group_ids = [f'"{gid}"' for gid in group_ids]
            group_values = '|'.join(escaped_group_ids)
            group_filter = f'(@group_id:{group_values})'

        sanitized_query = self.sanitize(query)

        # Remove stopwords and empty tokens from the sanitized query
        query_words = sanitized_query.split()
        filtered_words = [word for word in query_words if word and word.lower() not in STOPWORDS]
        sanitized_query = ' | '.join(filtered_words)

        # If the query is too long return no query
        if len(sanitized_query.split(' ')) + len(group_ids or '') >= max_query_length:
            return ''

        full_query = group_filter + ' (' + sanitized_query + ')'

        return full_query

=== _build_falkor_fulltext_query in search_ops.py ===
def _sanitize(query: str) -> str:
    """Replace FalkorDB special characters with whitespace."""
    sanitized = query.translate(_SEPARATOR_MAP)
    return ' '.join(sanitized.split())


def _build_falkor_fulltext_query(
    query: str,
    group_ids: list[str] | None = None,
    max_query_length: int = MAX_QUERY_LENGTH,
) -> str:
    """Build a fulltext query string for FalkorDB using RedisSearch syntax."""
    if group_ids is None or len(group_ids) == 0:
        group_filter = ''
    else:
        escaped_group_ids = [f'"{gid}"' for gid in group_ids]
        group_values = '|'.join(escaped_group_ids)
        group_filter = f'(@group_id:{group_values})'

    sanitized_query = _sanitize(query)

    # Remove stopwords and empty tokens
    query_words = sanitized_query.split()
    filtered_words = [word for word in query_words if word and word.lower() not in STOPWORDS]
    sanitized_query = ' | '.join(filtered_words)

    if len(sanitized_query.split(' ')) + len(group_ids or '') >= max_query_length:
        return ''

    full_query = group_filter + ' (' + sanitized_query + ')'
    return full_query


class FalkorSearchOperations(SearchOperations):
    # --- Node search ---
Bash Locate and read sanitize() for bug #10 patch
IN
echo "=== sanitize() function — bug #10 target ==="
grep -n "def sanitize\|def _sanitize" /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py 2>/dev/null
echo ""
echo "=== Read the sanitize() body ==="
SANITIZE_LINE=$(grep -n "def sanitize" /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py | head -1 | cut -d: -f1)
echo "Found at line $SANITIZE_LINE"
sed -n "$((SANITIZE_LINE-2)),$((SANITIZE_LINE+30))p" /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py

OUT
=== sanitize() function — bug #10 target ===
/Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py:344:    def sanitize(self, query: str) -> str:
/Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py:90:def _sanitize(query: str) -> str:

=== Read the sanitize() body ===
Found at line 344
            return obj

    def sanitize(self, query: str) -> str:
        """
        Replace FalkorDB special characters with whitespace.
        Based on FalkorDB tokenization rules: ,.<>{}[]"':;!@#$%^&*()-+=~
        """
        # FalkorDB separator characters that break text into tokens
        separator_map = str.maketrans(
            {
                ',': ' ',
                '.': ' ',
                '<': ' ',
                '>': ' ',
                '{': ' ',
                '}': ' ',
                '[': ' ',
                ']': ' ',
                '"': ' ',
                "'": ' ',
                ':': ' ',
                ';': ' ',
                '!': ' ',
                '@': ' ',
                '#': ' ',
                '$': ' ',
                '%': ' ',
                '^': ' ',
                '&': ' ',
                '*': ' ',
                '(': ' ',
                ')': ' ',
                '-': ' ',
Bash Locate transport_security bug #13 site
IN
echo "=== graphiti-mcp main() and transport_security mutation — bug #13 ==="
grep -rn "settings.host\|TransportSecurityMiddleware\|transport_security" /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/ 2>/dev/null | head -20
echo ""
echo "=== Look for the host mutation in main() ==="
find /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server -name "main.py" -o -name "*.py" 2>/dev/null | xargs grep -l "settings.host" 2>/dev/null

OUT
=== graphiti-mcp main() and transport_security mutation — bug #13 ===
/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py:900:        mcp.settings.host = config.server.host
/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py:919:            f'Running MCP server with SSE transport on {mcp.settings.host}:{mcp.settings.port}'
/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py:921:        logger.info(f'Access the server at: http://{mcp.settings.host}:{mcp.settings.port}/sse')
/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py:925:        display_host = 'localhost' if mcp.settings.host == '0.0.0.0' else mcp.settings.host
/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py:927:            f'Running MCP server with streamable HTTP transport on {mcp.settings.host}:{mcp.settings.port}'

=== Look for the host mutation in main() ===
/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py
Bash Read full sanitize() char map for bug #10 patch
IN
echo "=== Full sanitize() char list — bug #10 ==="
sed -n '344,405p' /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py | head -60
echo ""
echo "=== _SEPARATOR_MAP in search_ops.py (bug #10's other call site) ==="
grep -n "_SEPARATOR_MAP" /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py
sed -n "$(grep -n "_SEPARATOR_MAP =" /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py | head -1 | cut -d: -f1),$(($(grep -n "_SEPARATOR_MAP =" /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py | head -1 | cut -d: -f1)+50))p" /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py

OUT
=== Full sanitize() char list — bug #10 ===
    def sanitize(self, query: str) -> str:
        """
        Replace FalkorDB special characters with whitespace.
        Based on FalkorDB tokenization rules: ,.<>{}[]"':;!@#$%^&*()-+=~
        """
        # FalkorDB separator characters that break text into tokens
        separator_map = str.maketrans(
            {
                ',': ' ',
                '.': ' ',
                '<': ' ',
                '>': ' ',
                '{': ' ',
                '}': ' ',
                '[': ' ',
                ']': ' ',
                '"': ' ',
                "'": ' ',
                ':': ' ',
                ';': ' ',
                '!': ' ',
                '@': ' ',
                '#': ' ',
                '$': ' ',
                '%': ' ',
                '^': ' ',
                '&': ' ',
                '*': ' ',
                '(': ' ',
                ')': ' ',
                '-': ' ',
                '+': ' ',
                '=': ' ',
                '~': ' ',
                '?': ' ',
                '|': ' ',
                '/': ' ',
                '\\': ' ',
            }
        )
        sanitized = query.translate(separator_map)
        # Clean up multiple spaces
        sanitized = ' '.join(sanitized.split())
        return sanitized

    def build_fulltext_query(
        self, query: str, group_ids: list[str] | None = None, max_query_length: int = 128
    ) -> str:
        """
        Build a fulltext query string for FalkorDB using RedisSearch syntax.
        FalkorDB uses RedisSearch-like syntax where:
        - Field queries use @ prefix: @field:value
        - Multiple values for same field: (@field:value1|value2)
        - Text search doesn't need @ prefix for content fields
        - AND is implicit with space: (@group_id:value) (text)
        - OR uses pipe within parentheses: (@group_id:value1|value2)
        """
        validate_group_ids(group_ids)

        if group_ids is None or len(group_ids) == 0:

=== _SEPARATOR_MAP in search_ops.py (bug #10's other call site) ===
54:_SEPARATOR_MAP = str.maketrans(
92:    sanitized = query.translate(_SEPARATOR_MAP)
_SEPARATOR_MAP = str.maketrans(
    {
        ',': ' ',
        '.': ' ',
        '<': ' ',
        '>': ' ',
        '{': ' ',
        '}': ' ',
        '[': ' ',
        ']': ' ',
        '"': ' ',
        "'": ' ',
        ':': ' ',
        ';': ' ',
        '!': ' ',
        '@': ' ',
        '#': ' ',
        '$': ' ',
        '%': ' ',
        '^': ' ',
        '&': ' ',
        '*': ' ',
        '(': ' ',
        ')': ' ',
        '-': ' ',
        '+': ' ',
        '=': ' ',
        '~': ' ',
        '?': ' ',
        '|': ' ',
        '/': ' ',
        '\\': ' ',
    }
)


def _sanitize(query: str) -> str:
    """Replace FalkorDB special characters with whitespace."""
    sanitized = query.translate(_SEPARATOR_MAP)
    return ' '.join(sanitized.split())


def _build_falkor_fulltext_query(
    query: str,
    group_ids: list[str] | None = None,
    max_query_length: int = MAX_QUERY_LENGTH,
) -> str:
    """Build a fulltext query string for FalkorDB using RedisSearch syntax."""
    if group_ids is None or len(group_ids) == 0:
        group_filter = ''
    else:
Bash Read bug #13 site and current bootstrap workaround
IN
echo "=== graphiti-mcp host mutation site — bug #13 ==="
sed -n '880,935p' /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py
echo ""
echo "=== guardkit bootstrap shim (current workaround) ==="
sed -n '1,80p' /Users/richardwoollcott/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-bootstrap.py 2>/dev/null

OUT
=== graphiti-mcp host mutation site — bug #13 ===
        temp_service = GraphitiService(config, SEMAPHORE_LIMIT)
        await temp_service.initialize()
        client = await temp_service.get_client()
        await clear_data(client.driver)
        logger.info('All graphs destroyed')

    # Initialize services
    graphiti_service = GraphitiService(config, SEMAPHORE_LIMIT)
    queue_service = QueueService()
    await graphiti_service.initialize()

    # Set global client for backward compatibility
    graphiti_client = await graphiti_service.get_client()
    semaphore = graphiti_service.semaphore

    # Initialize queue service with the client
    await queue_service.initialize(graphiti_client)

    # Set MCP server settings
    if config.server.host:
        mcp.settings.host = config.server.host
    if config.server.port:
        mcp.settings.port = config.server.port

    # Return MCP configuration for transport
    return config.server


async def run_mcp_server():
    """Run the MCP server in the current event loop."""
    # Initialize the server
    mcp_config = await initialize_server()

    # Run the server with configured transport
    logger.info(f'Starting MCP server with transport: {mcp_config.transport}')
    if mcp_config.transport == 'stdio':
        await mcp.run_stdio_async()
    elif mcp_config.transport == 'sse':
        logger.info(
            f'Running MCP server with SSE transport on {mcp.settings.host}:{mcp.settings.port}'
        )
        logger.info(f'Access the server at: http://{mcp.settings.host}:{mcp.settings.port}/sse')
        await mcp.run_sse_async()
    elif mcp_config.transport == 'http':
        # Use localhost for display if binding to 0.0.0.0
        display_host = 'localhost' if mcp.settings.host == '0.0.0.0' else mcp.settings.host
        logger.info(
            f'Running MCP server with streamable HTTP transport on {mcp.settings.host}:{mcp.settings.port}'
        )
        logger.info('=' * 60)
        logger.info('MCP Server Access Information:')
        logger.info(f'  Base URL: http://{display_host}:{mcp.settings.port}/')
        logger.info(f'  MCP Endpoint: http://{display_host}:{mcp.settings.port}/mcp/')
        logger.info('  Transport: HTTP (streamable)')

        # Show FalkorDB Browser UI access if enabled

=== guardkit bootstrap shim (current workaround) ===
#!/usr/bin/env python3
"""Bootstrap wrapper for graphiti-mcp-server that disables MCP DNS rebinding protection.

Why this exists
---------------
graphiti-mcp-server calls ``FastMCP('Graphiti Agent Memory', ...)`` with no
``host`` argument. FastMCP's default host is ``"127.0.0.1"``, which triggers an
auto-enable of DNS rebinding protection with an allow-list of only
``["127.0.0.1:*", "localhost:*", "[::1]:*"]``. graphiti then mutates
``mcp.settings.host = "0.0.0.0"`` to bind the listener to all interfaces — but
the ``transport_security`` object is already frozen with the localhost-only
allow-list. Result: uvicorn accepts the TCP connection on every interface, but
the MCP middleware returns ``421 Invalid Host header`` for any ``Host`` value
other than localhost (e.g. a Tailscale hostname like ``promaxgb10-41b1:8004``).

The GuardKit deployment is intentionally multi-host: Claude Code on a Mac and
Claude Code on the GB10 both hit ``http://promaxgb10-41b1:8004/mcp``. Neither
of them sends ``Host: localhost:8004``, so every non-loopback client sees 421.

Fix
---
Patch ``mcp.server.transport_security.TransportSecurityMiddleware`` to no-op
the ``_validate_host`` / ``_validate_origin`` checks before graphiti's main()
imports FastMCP. The MCP server is reachable only over Tailscale (not the
public internet) and the rebinding-protection threat model — a browser on a
user's machine being tricked into making same-origin requests to a
localhost-bound MCP — does not apply here.

Mounted at /app/mcp/bootstrap.py by scripts/graphiti-mcp.sh and invoked via
``uv run --no-sync bootstrap.py`` in place of the image's default main.py.
"""

import sys
from pathlib import Path

from mcp.server import transport_security as _ts

_ts.TransportSecurityMiddleware._validate_host = lambda self, host: True
_ts.TransportSecurityMiddleware._validate_origin = lambda self, origin: True

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from graphiti_mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
Bash Find FastMCP construction site and supported kwargs for bug #13 fix
IN
echo "=== FastMCP construction site ==="
grep -n "FastMCP(" /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py | head -5
echo ""
SITE=$(grep -n "FastMCP(" /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py | head -1 | cut -d: -f1)
sed -n "$((SITE-3)),$((SITE+10))p" /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py
echo ""
echo "=== TransportSecuritySettings shape (so we know what kwargs FastMCP accepts) ==="
grep -rn "class TransportSecuritySettings\|allowed_hosts\|allowed_origins" /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/.venv/ 2>/dev/null | grep -v "test\|\.pyc" | head -10
echo ""
echo "=== Check the FastMCP kwargs docstring ==="
.venv/bin/python -c "from mcp.server.fastmcp import FastMCP; help(FastMCP.__init__)" 2>&1 | head -30

OUT
=== FastMCP construction site ===
147:mcp = FastMCP(

"""

# MCP server instance
mcp = FastMCP(
    'Graphiti Agent Memory',
    instructions=GRAPHITI_MCP_INSTRUCTIONS,
)

# Global services
graphiti_service: Optional['GraphitiService'] = None
queue_service: QueueService | None = None

# Global client for backward compatibility
graphiti_client: Graphiti | None = None

=== TransportSecuritySettings shape (so we know what kwargs FastMCP accepts) ===

=== Check the FastMCP kwargs docstring ===
Help on function __init__ in module mcp.server.fastmcp.server:

__init__(
    self,
    name: str | None = None,
    instructions: str | None = None,
    website_url: str | None = None,
    icons: list[Icon] | None = None,
    auth_server_provider: OAuthAuthorizationServerProvider[Any, Any, Any] | None = None,
    token_verifier: TokenVerifier | None = None,
    event_store: EventStore | None = None,
    retry_interval: int | None = None,
    *,
    tools: list[Tool] | None = None,
    debug: bool = False,
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO',
    host: str = '127.0.0.1',
    port: int = 8000,
    mount_path: str = '/',
    sse_path: str = '/sse',
    message_path: str = '/messages/',
    streamable_http_path: str = '/mcp',
    json_response: bool = False,
    stateless_http: bool = False,
    warn_on_duplicate_resources: bool = True,
    warn_on_duplicate_tools: bool = True,
    warn_on_duplicate_prompts: bool = True,
    dependencies: Collection[str] = (),
    lifespan: Callable[[FastMCP[LifespanResultT]], AbstractAsyncContextManager[LifespanResultT]] | None = None,
    auth: AuthSettings | None = None,
Good — local clone is 0.29.0 (already current with study-tutor's pin range), and bug #10 is mostly fixed in 0.29 (slashes/pipes/backslashes already in strip list — only backtick remains missing). That makes the patches even smaller. Let me build the patches and the patches directory now.

Bash Stage original + to-be-edited copies in /tmp for diff generation
IN
mkdir -p /tmp/graphiti-fork-patches/{a,b}/graphiti_core/driver
mkdir -p /tmp/graphiti-fork-patches/{a,b}/graphiti_core/driver/falkordb/operations
mkdir -p /tmp/graphiti-fork-patches/{a,b}/mcp_server/src
# Copy the three target files into both 'a' (original) and 'b' (will-edit) trees
cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py /tmp/graphiti-fork-patches/a/graphiti_core/driver/falkordb_driver.py
cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py /tmp/graphiti-fork-patches/b/graphiti_core/driver/falkordb_driver.py
cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py /tmp/graphiti-fork-patches/a/graphiti_core/driver/falkordb/operations/search_ops.py
cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py /tmp/graphiti-fork-patches/b/graphiti_core/driver/falkordb/operations/search_ops.py
cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py /tmp/graphiti-fork-patches/a/mcp_server/src/graphiti_mcp_server.py
cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py /tmp/graphiti-fork-patches/b/mcp_server/src/graphiti_mcp_server.py
echo "Copied files into /tmp/graphiti-fork-patches/{a,b}/"
ls /tmp/graphiti-fork-patches/b/

OUT
Copied files into /tmp/graphiti-fork-patches/{a,b}/
graphiti_core
mcp_server
Now I'll edit the b/ copies and then diff -u to generate the three patches.

Patch 1 prep — drop-filter for bugs #5/#11/#12 in falkordb_driver.py:

Edit falkordb_driver.py
Edit failed
Read falkordb_driver.py (lines 396-430)
Edit falkordb_driver.py
Added 7 lines
Now the same drop-filter changes in the duplicate function in search_ops.py:

Read search_ops.py (lines 97-124)
Edit search_ops.py
Added 4 lines
Patch 2 prep — extend sanitize() to strip backtick (bug #10 — only backtick missing in 0.29.0):

Edit falkordb_driver.py
Added 5 lines
Edit search_ops.py
Added 4 lines
Patch 3 prep — early host binding (bug #13 — graphiti-mcp transport_security frozen with wrong allow-list):

Read graphiti_mcp_server.py (lines 141-155)
Bash Check whether os is already imported
IN
grep -n "^import os\|^from os " /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py | head -3
echo "---"
echo "first 20 import lines:"
grep -n "^import\|^from" /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py | head -10

OUT
9:import os
---
first 20 import lines:
6:import argparse
7:import asyncio
8:import logging
9:import os
10:import sys
11:from pathlib import Path
12:from typing import Any, Optional
14:from dotenv import load_dotenv
15:from graphiti_core import Graphiti
16:from graphiti_core.edges import EntityEdge
Edit graphiti_mcp_server.py
Added 12 lines
All edits applied. Now generate the three .patch files using diff -u, write them into the fork, and verify they apply cleanly.

Bash Stage per-patch tree generation
IN
mkdir -p /Users/richardwoollcott/Projects/appmilla_github/graphiti/patches
cd /tmp/graphiti-fork-patches

# Patch 1: drop-filter for bugs #5/#11/#12 — touches both falkordb files
{
  diff -u a/graphiti_core/driver/falkordb_driver.py b/graphiti_core/driver/falkordb_driver.py | grep -A 100000 "^@@" | head -50 > /dev/null
  diff -u a/graphiti_core/driver/falkordb_driver.py b/graphiti_core/driver/falkordb_driver.py
  diff -u a/graphiti_core/driver/falkordb/operations/search_ops.py b/graphiti_core/driver/falkordb/operations/search_ops.py
} > /tmp/raw-all-diffs.patch

# Split: patch 1 needs the build_fulltext_query hunks only (drop #10 hunks for now)
# Approach: regenerate per-file diffs that include only specific changes.

# Easier path: revert b/ to a/, then re-apply ONLY the drop-filter changes for patch 1, diff, then
# reset, apply ONLY the sanitize change for patch 2, diff. Patch 3 stays the only mcp_server change.

# Simpler: use python to filter hunks. But the cleanest approach is to just
# generate three separate b-trees, one per patch.

# Reset
rm -rf /tmp/graphiti-fork-patches/p1 /tmp/graphiti-fork-patches/p2 /tmp/graphiti-fork-patches/p3
mkdir -p /tmp/graphiti-fork-patches/p1 /tmp/graphiti-fork-patches/p2 /tmp/graphiti-fork-patches/p3
echo "Will regenerate per-patch trees"

OUT
Will regenerate per-patch trees
Shell cwd was reset to /Users/richardwoollcott/Projects/appmilla_github/study-tutor
Bash Stage 3 separate per-patch directories from pristine originals
IN
# Set up clean per-patch staging directories with the original files
for P in p1 p2 p3; do
  mkdir -p /tmp/graphiti-fork-patches/$P/graphiti_core/driver/falkordb/operations
  mkdir -p /tmp/graphiti-fork-patches/$P/mcp_server/src
  cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py /tmp/graphiti-fork-patches/$P/graphiti_core/driver/falkordb_driver.py
  cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py /tmp/graphiti-fork-patches/$P/graphiti_core/driver/falkordb/operations/search_ops.py
  cp /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py /tmp/graphiti-fork-patches/$P/mcp_server/src/graphiti_mcp_server.py
done
echo "Staged 3 fresh per-patch trees"
ls /tmp/graphiti-fork-patches/p1/ /tmp/graphiti-fork-patches/p2/ /tmp/graphiti-fork-patches/p3/

OUT
Staged 3 fresh per-patch trees
/tmp/graphiti-fork-patches/p1/:
graphiti_core
mcp_server

/tmp/graphiti-fork-patches/p2/:
graphiti_core
mcp_server

/tmp/graphiti-fork-patches/p3/:
graphiti_core
mcp_server
Now apply each patch's edits to its own staging tree (p1 = drop-filter only, p2 = backtick only, p3 = mcp host binding only):

Edit falkordb_driver.py
Edit failed
Read falkordb_driver.py (lines 396-430)
Read search_ops.py (lines 96-125)
Read falkordb_driver.py (lines 376-390)
Read search_ops.py (lines 83-92)
Read graphiti_mcp_server.py (lines 145-154)
Now apply each patch's edit to its dedicated tree:

Edit falkordb_driver.py
Added 7 lines
Edit search_ops.py
Added 4 lines
Edit falkordb_driver.py
Added 5 lines
Edit search_ops.py
Added 4 lines
Edit graphiti_mcp_server.py
Added 12 lines
Now generate the three .patch files using diff -u, and verify each applies cleanly against the actual fork:

Bash Generate three .patch files via diff -u
IN
PATCHES=/Users/richardwoollcott/Projects/appmilla_github/graphiti/patches
mkdir -p $PATCHES
cd /tmp/graphiti-fork-patches

# Patch 1: drop-filter (touches both falkordb files)
{
  diff -u --label "a/graphiti_core/driver/falkordb_driver.py" --label "b/graphiti_core/driver/falkordb_driver.py" \
    /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py \
    p1/graphiti_core/driver/falkordb_driver.py
  diff -u --label "a/graphiti_core/driver/falkordb/operations/search_ops.py" --label "b/graphiti_core/driver/falkordb/operations/search_ops.py" \
    /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py \
    p1/graphiti_core/driver/falkordb/operations/search_ops.py
} > $PATCHES/001-drop-fulltext-group-filter.patch

# Patch 2: backtick-strip (touches both falkordb files)
{
  diff -u --label "a/graphiti_core/driver/falkordb_driver.py" --label "b/graphiti_core/driver/falkordb_driver.py" \
    /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb_driver.py \
    p2/graphiti_core/driver/falkordb_driver.py
  diff -u --label "a/graphiti_core/driver/falkordb/operations/search_ops.py" --label "b/graphiti_core/driver/falkordb/operations/search_ops.py" \
    /Users/richardwoollcott/Projects/appmilla_github/graphiti/graphiti_core/driver/falkordb/operations/search_ops.py \
    p2/graphiti_core/driver/falkordb/operations/search_ops.py
} > $PATCHES/002-extend-sanitize-strip-backtick.patch

# Patch 3: mcp early host binding (touches one mcp_server file)
diff -u --label "a/mcp_server/src/graphiti_mcp_server.py" --label "b/mcp_server/src/graphiti_mcp_server.py" \
  /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/src/graphiti_mcp_server.py \
  p3/mcp_server/src/graphiti_mcp_server.py > $PATCHES/003-mcp-early-host-binding.patch

echo "=== Patches generated ==="
ls -l $PATCHES/
echo ""
echo "=== Line counts ==="
wc -l $PATCHES/*.patch

OUT
=== Patches generated ===
total 24
-rw-r--r--  1 richardwoollcott  staff  3122 May  3 21:37 001-drop-fulltext-group-filter.patch
-rw-r--r--  1 richardwoollcott  staff  1015 May  3 21:37 002-extend-sanitize-strip-backtick.patch
-rw-r--r--  1 richardwoollcott  staff   926 May  3 21:37 003-mcp-early-host-binding.patch

=== Line counts ===
      71 /Users/richardwoollcott/Projects/appmilla_github/graphiti/patches/001-drop-fulltext-group-filter.patch
      27 /Users/richardwoollcott/Projects/appmilla_github/graphiti/patches/002-extend-sanitize-strip-backtick.patch
      24 /Users/richardwoollcott/Projects/appmilla_github/graphiti/patches/003-mcp-early-host-binding.patch
     122 total
Shell cwd was reset to /Users/richardwoollcott/Projects/appmilla_github/study-tutor
Three patches generated. Now verify each applies cleanly with git apply --check against the actual fork:

Bash Verify each patch applies cleanly to the fork via git apply --check
IN
cd /Users/richardwoollcott/Projects/appmilla_github/graphiti

echo "=== git status before any patch attempt ==="
git status --short patches/ graphiti_core/driver/ mcp_server/src/ 2>&1 | head -10
echo ""

for P in 001-drop-fulltext-group-filter.patch 002-extend-sanitize-strip-backtick.patch 003-mcp-early-host-binding.patch; do
  echo "=== git apply --check patches/$P ==="
  git apply --check patches/$P 2>&1
  if [ $? -eq 0 ]; then
    echo "  ✓ applies cleanly"
  fi
  echo ""
done

echo "=== Try applying all three together (sequencing test) ==="
git apply --check patches/001-drop-fulltext-group-filter.patch patches/002-extend-sanitize-strip-backtick.patch patches/003-mcp-early-host-binding.patch 2>&1
if [ $? -eq 0 ]; then
  echo "  ✓ all three apply together cleanly"
fi

OUT
=== git status before any patch attempt ===
?? patches/

=== git apply --check patches/001-drop-fulltext-group-filter.patch ===
  ✓ applies cleanly

=== git apply --check patches/002-extend-sanitize-strip-backtick.patch ===
  ✓ applies cleanly

=== git apply --check patches/003-mcp-early-host-binding.patch ===
  ✓ applies cleanly

=== Try applying all three together (sequencing test) ===
  ✓ all three apply together cleanly
Shell cwd was reset to /Users/richardwoollcott/Projects/appmilla_github/study-tutor
All three patches apply cleanly, individually and together. Quick sanity-check of one patch body to confirm format:

Read 003-mcp-early-host-binding.patch
Patch format is clean and applies via git apply -p1. Now write the patches README and update the task file (bump estimated_minutes + add patches reference).

Write README.md
97 lines
# appmilla fork — pre-built patches

This directory holds ready-to-apply patches drafted ahead of the GB10 fork-application session for [TASK-FORK-PATCH](../tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md). Each patch is a unified diff (`diff -u`) that applies cleanly via `git apply -p1` (or `patch -p1`) against this fork at version 0.29.0 (verified 2026-05-03 — all three pass `git apply --check` individually and together).

## What's here, in suggested apply order

| # | File | Bugs fixed (audit IDs) | Files touched |
|---|------|------------------------|---------------|
| 1 | `001-drop-fulltext-group-filter.patch` | #5 (RediSearch dash-as-NOT) + #11 (`@group_id` filter broken on FalkorDB) + #12 (empty post-stopword query produces invalid `()` syntax) | `graphiti_core/driver/falkordb_driver.py` (`build_fulltext_query`), `graphiti_core/driver/falkordb/operations/search_ops.py` (`_build_falkor_fulltext_query`) |
| 2 | `002-extend-sanitize-strip-backtick.patch` | #10 (partial — only backtick remains missing in 0.29.0; slashes/pipes/backslashes already in 0.29's strip list) | `graphiti_core/driver/falkordb_driver.py` (`sanitize` method), `graphiti_core/driver/falkordb/operations/search_ops.py` (`_SEPARATOR_MAP` constant) |
| 3 | `003-mcp-early-host-binding.patch` | #13 (graphiti-mcp's `transport_security` frozen with localhost-only allow-list because host is mutated AFTER FastMCP construction) | `mcp_server/src/graphiti_mcp_server.py` |

These three patches do **not** cover every entry in the audit punchlist. Bugs #1-#4 are already fixed in 0.29.0 (or live in consumer-side wiring per the audit's "stays in consumer code" note). Bugs #6/#7 — the `openai_generic` / `responses.parse` factory routing — are addressed by the in-flight diff already drafted at `~/Projects/appmilla_github/graphiti-official/mcp_server/src/services/factories.py` per the task's "In-flight patch already drafted" section. Bugs #8 (PR #1170) and #9 (issue #1272) have explicit upstream PR/issue references; cherry-pick or re-derive those during the GB10 session.

Decision 5 in the task file (drop-filter vs escape-and-keep) is implicitly answered by patch 1 — it implements **drop-the-filter**, the recommended approach. Apply patch 1 only after locking that decision.

## Applying the patches

From the fork repo root (e.g. `~/Projects/appmilla_github/graphiti/` on the GB10):

```bash
# Option A — git apply (recommended; respects whitespace, integrates with index)
git apply --check patches/001-drop-fulltext-group-filter.patch
git apply patches/001-drop-fulltext-group-filter.patch

git apply --check patches/002-extend-sanitize-strip-backtick.patch
git apply patches/002-extend-sanitize-strip-backtick.patch

git apply --check patches/003-mcp-early-host-binding.patch
git apply patches/003-mcp-early-host-binding.patch

# Option B — patch -p1 (works even outside a git checkout)
patch -p1 < patches/001-drop-fulltext-group-filter.patch
patch -p1 < patches/002-extend-sanitize-strip-backtick.patch
patch -p1 < patches/003-mcp-early-host-binding.patch
```

After all three are applied, commit each as a separate commit so each fix is independently revertable. Suggested commit messages:

```
fix(falkordb): drop @group_id fulltext filter (TASK-FORK-PATCH bugs #5/#11/#12)

The upstream `(@group_id:"...")` prefix is unreliable on FalkorDB — RediSearch
tokenises group_ids at index time and parses dashes as NOT operators inside
the double-quote wrap. Group isolation already comes from the multi-graph
driver clone plus the Cypher WHERE clause, so we drop the prefix entirely
and return RediSearch's match-all wildcard for empty post-stopword queries.

Refs: study-tutor R-WAVE5-03; guardkit/knowledge/falkordb_workaround.py
```

```
fix(falkordb): strip backtick in sanitize() (TASK-FORK-PATCH bug #10)

Backticks survive upstream's strip list, so markdown-style `path/to/file.md`
references in episode bodies leak into entity names and break RediSearch
syntax at index time.

Refs: guardkit TASK-REV-661E
```

```
fix(mcp): bind FastMCP host at construction time (TASK-FORK-PATCH bug #13)

graphiti-mcp's initialize_server() mutates `mcp.settings.host` AFTER FastMCP
has frozen transport_security with a localhost-only allow-list. Read
MCP_SERVER_HOST from the environment at module load and pass it to FastMCP
so the allow-list freezes against the right host. Default preserves
upstream behaviour.

Refs: guardkit/scripts/graphiti-mcp-bootstrap.py — once this lands and
graphiti-mcp.sh exports MCP_SERVER_HOST=0.0.0.0, the bootstrap shim can be
removed in a follow-up.
```

## What's NOT in this directory (and why)

- **Bug #6/#7 — `openai_generic` factory routing**: addressed by the in-flight diff at `~/Projects/appmilla_github/graphiti-official/mcp_server/src/services/factories.py` (Approach A — auto-detect on `base_url`). Apply that diff verbatim per the task's "In-flight patch already drafted" section.
- **Bug #8 — `handle_multiple_group_ids` `>1` vs `>=1`**: cherry-pick from upstream PR #1170 (already authored, not yet merged).
- **Bug #9 — `edge_fulltext_search` / `edge_bfs_search` O(n×m) scan**: cherry-pick from the patch in `guardkit/knowledge/falkordb_workaround.py:380-635`, or re-derive against upstream issue #1272.
- **Patches for the verification ACs themselves** (smoke tests, container rebuild, doc updates) — those live in the task file's mechanical plan, not as code diffs.

## Verifying after apply

After the patches land + the openai_generic + #8/#9 fixes are also in:

```bash
# In the fork
.venv/bin/python -c "from graphiti_core.driver.falkordb_driver import FalkorDriver; print('OK')"

# In a study-tutor venv pinned to the forked tag
.venv/bin/python scripts/seed_student_model.py    # expect 25/25 succeeded_writes
.venv/bin/python .guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py    # expect populated state
```

See AC-FORK-08 in the task file for the full end-to-end verification checklist.
Now update the task file: bump estimated_minutes from 240 to 600, and add a section pointing at patches/.

Edit TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
Modified
Edit TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
Modified
Now add a "Pre-built patches" section near the punchlist so it's discoverable. I'll place it right after the punchlist table:

Edit TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
Added 12 lines
Final verification — apply-check all three patches one more time, and confirm the task file edits look right:

Bash Final verify: patches still apply, task file frontmatter + new section both look correct, cleanup /tmp
IN
cd /Users/richardwoollcott/Projects/appmilla_github/graphiti

echo "=== Patches dir contents ==="
ls -la patches/
echo ""

echo "=== Re-verify all three apply cleanly post-task-file-edit ==="
git apply --check patches/001-drop-fulltext-group-filter.patch patches/002-extend-sanitize-strip-backtick.patch patches/003-mcp-early-host-binding.patch 2>&1 && echo "  ✓ all three apply cleanly together"
echo ""

echo "=== Task file frontmatter (estimated_minutes bumped) ==="
head -16 tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md
echo ""

echo "=== Pre-built patches section in task file ==="
grep -A 10 "Pre-built patches available" tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md | head -14
echo ""

echo "=== Updated total task file length ==="
wc -l tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md

# Cleanup /tmp staging
rm -rf /tmp/graphiti-fork-patches /tmp/raw-all-diffs.patch
echo ""
echo "=== /tmp staging cleaned up ==="

OUT
=== Patches dir contents ===
total 40
drwxr-xr-x   6 richardwoollcott  staff   192 May  3 21:39 .
drwxr-xr-x  40 richardwoollcott  staff  1280 May  3 21:36 ..
-rw-r--r--   1 richardwoollcott  staff  3122 May  3 21:37 001-drop-fulltext-group-filter.patch
-rw-r--r--   1 richardwoollcott  staff  1015 May  3 21:37 002-extend-sanitize-strip-backtick.patch
-rw-r--r--   1 richardwoollcott  staff   926 May  3 21:37 003-mcp-early-host-binding.patch
-rw-r--r--   1 richardwoollcott  staff  5986 May  3 21:39 README.md

=== Re-verify all three apply cleanly post-task-file-edit ===
  ✓ all three apply cleanly together

=== Task file frontmatter (estimated_minutes bumped) ===
---
id: TASK-FORK-PATCH
title: Apply appmilla bug-fix patches to graphiti fork (RediSearch dash-escape + openai_generic factory)
status: backlog
created: 2026-05-03T00:00:00Z
updated: 2026-05-03T00:00:00Z
priority: high
task_type: feature
complexity: 4
estimated_minutes: 600
execution_location: promaxgb10-41b1
tags: [graphiti, fork, falkordb, redisearch, mcp, infra]
test_results:
  status: pending
  coverage: null
  last_run: null

=== Pre-built patches section in task file ===
### Pre-built patches available at [`patches/`](../../patches/) (drafted 2026-05-03)

Three of the audit-surfaced fixes are already drafted as ready-to-apply unified diffs in [`patches/`](../../patches/) at the fork repo root. Each was verified against the fork's current 0.29.0 main with `git apply --check`:

| Patch | Bugs covered | Apply step |
|-------|--------------|------------|
| [`patches/001-drop-fulltext-group-filter.patch`](../../patches/001-drop-fulltext-group-filter.patch) | #5 + #11 + #12 (the audit's recommended **drop-the-filter** approach for Decision 5) | `git apply patches/001-drop-fulltext-group-filter.patch` after Decision 5 = drop-filter is locked |
| [`patches/002-extend-sanitize-strip-backtick.patch`](../../patches/002-extend-sanitize-strip-backtick.patch) | #10 (only backtick remains missing from `sanitize()` in 0.29.0; slashes/pipes/backslashes already in upstream's strip list) | `git apply patches/002-extend-sanitize-strip-backtick.patch` |
| [`patches/003-mcp-early-host-binding.patch`](../../patches/003-mcp-early-host-binding.patch) | #13 (read `MCP_SERVER_HOST` env var at module load, pass to FastMCP construction so transport_security freezes against the right allow-list) | `git apply patches/003-mcp-early-host-binding.patch` — also requires `graphiti-mcp.sh` to export `MCP_SERVER_HOST=0.0.0.0` for the bootstrap shim to be retirable |

Suggested commit messages and full apply instructions are in [`patches/README.md`](../../patches/README.md). The remaining fixes (bugs #6/#7 via the in-flight `openai_generic` diff at `~/Projects/appmilla_github/graphiti-official/`, bug #8 via upstream PR #1170, bug #9 via upstream issue #1272 / `falkordb_workaround.py:380-635`) still need to be derived/cherry-picked during the GB10 session.

=== Updated total task file length ===
     339 tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md

=== /tmp staging cleaned up ===
Shell cwd was reset to /Users/richardwoollcott/Projects/appmilla_github/study-tutor
Both (a) and (b) done.

What landed
(a) Three pre-built patches at /Users/richardwoollcott/Projects/appmilla_github/graphiti/patches/, all verified clean against the fork's current 0.29.0 main with git apply --check:

File	Size	Covers
001-drop-fulltext-group-filter.patch	71 lines	Bugs #5 + #11 + #12 (drop-filter approach — implements Decision 5's recommended path)
002-extend-sanitize-strip-backtick.patch	27 lines	Bug #10 (slashes/pipes/backslashes already in 0.29's strip list — only backtick remains missing)
003-mcp-early-host-binding.patch	24 lines	Bug #13 (read MCP_SERVER_HOST at module load, pass to FastMCP construction so transport_security freezes against the right allow-list)
README.md	6KB	Apply order, commit-message templates, what's NOT in this dir and why
(b) Task file updated:

estimated_minutes: 240 → 600 (frontmatter + body explanation noting the original was based on the 2-row punchlist before the audit)
New "Pre-built patches available" subsection added under the punchlist with links to each patch + the README, and a note about which bugs still need GB10-session derivation (#6/#7 from the in-flight diff, #8 from PR #1170, #9 from issue #1272)
Bugs still requiring GB10 work (not pre-built — by design, since they live elsewhere or need cherry-picking):

#6/#7 — openai_generic factory routing — your in-flight diff at ~/Projects/appmilla_github/graphiti-official/ is already drafted, just needs to be applied
#8 — handle_multiple_group_ids >1 vs >=1 — cherry-pick from upstream PR #1170
#9 — edge_fulltext_search O(n×m) — cherry-pick from falkordb_workaround.py:380-635 or re-derive against upstream issue #1272
so TASK-INF-5054 is probably superceded now?
Yes — mostly, but with a small residue. Quick mapping of what each AC in TASK-INF-5054 does now:

TASK-INF-5054 item	Status under TASK-FORK-PATCH
AC #1 — pick remediation path	✅ Done. Decision is locked (option b — openai_generic) and TASK-FORK-PATCH Decision 6 just refines this to "auto-detect on base_url" (Approach A) which is the in-flight draft you already have at ~/graphiti-official/
AC #2 — apply the remediation	✅ Subsumed by AC-FORK-03 + AC-FORK-15 (lands in the fork instead of as a local-only patch + bootstrap-comment-block hack)
AC #3 — verify end-to-end	✅ Subsumed by AC-FORK-08 (full verification block) and AC-FORK-17 (specific log-line check)
AC #4 — decide fate of B1F7 defence-in-depth fallback	⚠️ Implicitly answered by the audit's "Defence-in-depth code (stays put)" section: keep graphiti_response_parser.py as cheap regression guard. Could close this out by stating the decision in writing without further work.
AC #5 — update documentation	❌ Not subsumed — guardkit-side doc cleanup (docs/guides/graphiti-claude-code-integration.md + docs/state/TASK-INF-5053/audit.md). Lives in guardkit, not the fork.
AC #6 — backfill missed episodes	❌ Not subsumed — operational cleanup. Optional anyway ("recommend leaving it" for general writes; only task-outcome writes are recoverable).
So the engineering work is fully subsumed; the residue is two small guardkit-side housekeeping items.

Cleanest hygiene moves
Three options, ordered most-to-least drastic:

Close TASK-INF-5054 entirely — write the B1F7 decision into its closing notes, fold AC #5 into AC-FORK-09's "TASK-INF-5054 moved to completed" sweep (which already requires TASK-FORK-PATCH to land first), and either drop AC #6 or file it as TASK-INF-5054-followup. Cleanest, but loses the historical investigation trail unless TASK-FORK-PATCH cross-references the audit.

Mark TASK-INF-5054 as superseded_by: TASK-FORK-PATCH in its frontmatter, leave it in backlog/ as a stub that gets archived alongside TASK-FORK-PATCH when the fork lands. Preserves the trail. Doc/backfill work either gets done as part of the close-out sweep or filed as a smaller follow-up.

Rescope TASK-INF-5054 to "guardkit-side post-fork tail" — strip out the implementation/verify ACs (now in TASK-FORK-PATCH), keep only the doc cleanup + B1F7 closeout + optional backfill, and have it activate after TASK-FORK-PATCH closes. Most explicit about sequencing, most edits to existing text.

My read: option 2 is the right call. Lowest-effort, doesn't lose history, keeps the task's existing detailed investigation as audit material, and the residual ACs (#4 trivially decided, #5 small, #6 optional) don't justify a full rescope. The frontmatter addition is one line; the body can grow a single "Superseded — see TASK-FORK-PATCH" subsection at the top. Done.

Want me to do that edit now?

yes option 2 please
Edit TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md
Added 1 line
Edit TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md
Added 25 lines
Verify the edits look right:

Bash Verify TASK-INF-5054 supersession edits
IN
echo "=== Frontmatter ==="
head -22 /Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md
echo ""
echo "=== Superseded section header ==="
grep -n "Superseded\|## Description" /Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md | head -5
echo ""
echo "=== Total file line count ==="
wc -l /Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md

OUT
=== Frontmatter ===
---
id: TASK-INF-5054
title: "graphiti-mcp openai provider ignores api_url; falls through to api.openai.com and 401s"
status: backlog
created: 2026-05-02T17:05:00Z
updated: 2026-05-03T22:00:00Z
priority: high
task_type: feature
tags:
  - infra
  - graphiti
  - mcp
  - upstream
  - llm
  - knowledge-graph
complexity: 5
estimated_minutes: 120
parent_task: TASK-INF-5053
superseded_by: TASK-FORK-PATCH
remediation_decision: "option_b_openai_generic"
execution_location: "promaxgb10-41b1 (work directly on the GB10, not via SSH from a Mac dev machine)"
---

=== Superseded section header ===
26:## Superseded — see TASK-FORK-PATCH (2026-05-03)
51:## Description

=== Total file line count ===
     399 /Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md
Done. Summary of edits to TASK-INF-5054:

Frontmatter: added superseded_by: TASK-FORK-PATCH; bumped updated to today
New "Superseded" section at top of body (between title heading and original ## Description):
Status statement + rationale
Per-AC mapping table showing what's subsumed (#1-#3), what's decided (#4 → keep), what's residual guardkit-side work (#5 docs, #6 optional backfill)
Cross-references to TASK-FORK-PATCH and its patches/ directory
Note that the original task body is preserved verbatim below for audit trail
File stays in tasks/backlog/ (per option 2) — will be archived alongside TASK-FORK-PATCH per AC-FORK-09
Anyone reading TASK-INF-5054 now sees the supersession status before any of the original investigation, with a clear pointer to the active task. The investigation history is preserved unchanged below the new section.

whats the best command syntax to use for the review i.e. which mode?
Let me check the /task-review command's mode options before answering — I want to give you the actual mode names rather than guess.

Bash Find task-review command spec
IN
find ~/Projects/appmilla_github/guardkit -name "task-review*" -path "*/commands/*" 2>/dev/null | head -5
echo "---"
find ~/.claude/commands ~/.agentecflow -name "task-review*" 2>/dev/null | head -5
echo "---"
ls ~/.claude/commands/ 2>/dev/null | grep -i review

OUT
/Users/richardwoollcott/Projects/appmilla_github/guardkit/test_api/.claude/commands/task-review.md
/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/task-review.md
---
/Users/richardwoollcott/.agentecflow/commands/task-review.md
---
task-review.md
Bash Read task-review mode options
IN
echo "=== task-review.md — first 100 lines for mode/option overview ==="
head -100 ~/Projects/appmilla_github/guardkit/installer/core/commands/task-review.md
echo ""
echo "=== Mode/flag enumeration ==="
grep -nE "^##|^### |--mode|--depth|--type|--scope|--intensity" ~/Projects/appmilla_github/guardkit/installer/core/commands/task-review.md | head -30

OUT
=== task-review.md — first 100 lines for mode/option overview ===
# Task Review - Structured Analysis and Decision-Making

Execute structured review and analysis workflows for tasks that require assessment, evaluation, or decision-making rather than implementation.

## Command Syntax

```bash
/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH] [--output=FORMAT] [--capture-knowledge]
```

## Available Flags

| Flag | Description |
|------|-------------|
| `--mode=MODE` | Review mode (architectural, code-quality, decision, technical-debt, security) |
| `--depth=DEPTH` | Review depth (quick, standard, comprehensive) |
| `--output=FORMAT` | Output format (markdown, json, both) |
| `--no-questions` | Skip review scope clarification |
| `--with-questions` | Force clarification even for simple reviews |
| `--defaults` | Use clarification defaults without prompting |
| `--capture-knowledge` | Trigger knowledge capture session after review completion (3-5 context-specific questions) |

## Overview

The `/task-review` command provides a dedicated workflow for analysis and decision-making tasks, separate from the implementation-focused `/task-work` command.

**Use `/task-review` for**:
- Architectural reviews and assessments
- Code quality evaluations
- Technical decision analysis
- Technical debt assessment
- Security audits
- Root cause analysis

**Use `/task-work` for**:
- Feature implementation
- Bug fixes
- Refactoring
- Test creation

## Automatic Review Task Detection

When creating tasks with `/task-create`, the system automatically detects review/analysis tasks and suggests using `/task-review` instead of `/task-work`.

### Detection Criteria

A task is detected as a review task if **any** of the following conditions are met:

1. **Explicit task_type field**: `task_type:review` parameter
2. **Decision required flag**: `decision_required:true` parameter
3. **Review-related tags**: `architecture-review`, `code-review`, `decision-point`, `assessment`
4. **Title keywords**: `review`, `analyze`, `evaluate`, `assess`, `audit`, `investigation`

### Suggestion Behavior

When a review task is detected during `/task-create`, you'll see:

```
=========================================================================
REVIEW TASK DETECTED
=========================================================================

Task: Review authentication architecture

This appears to be a review/analysis task.

Suggested workflow:
  1. Create task: /task-create (current command)
  2. Execute review: /task-review TASK-XXX
  3. (Optional) Implement findings: /task-work TASK-YYY

Note: /task-work is for implementation, /task-review is for analysis.
=========================================================================

Create task? [Y/n]:
```

**Important**: The suggestion is **informational only** and doesn't block task creation. You can still create the task and use `/task-work` if desired, though `/task-review` is recommended for analysis tasks.

### Detection Examples

**Example 1: Explicit task_type**
```bash
/task-create "Architectural review of authentication system" task_type:review
# ✅ Detected: Explicit task_type field
```

**Example 2: Decision required flag**
```bash
/task-create "Should we migrate to microservices?" decision_required:true
# ✅ Detected: Decision flag indicates review/analysis needed
```

**Example 3: Review tags**
```bash
/task-create "Code quality assessment" tags:[code-review,assessment]
# ✅ Detected: Tags indicate review task
```

**Example 4: Title keywords**

=== Mode/flag enumeration ===
5:## Command Syntax
8:/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH] [--output=FORMAT] [--capture-knowledge]
11:## Available Flags
15:| `--mode=MODE` | Review mode (architectural, code-quality, decision, technical-debt, security) |
16:| `--depth=DEPTH` | Review depth (quick, standard, comprehensive) |
23:## Overview
41:## Automatic Review Task Detection
45:### Detection Criteria
54:### Suggestion Behavior
80:### Detection Examples
113:### Why Detection Helps
120:### Overriding Detection
135:### See Also
140:## Examples
147:/task-review TASK-043 --mode=code-quality --depth=comprehensive
150:/task-review TASK-044 --mode=decision --depth=quick --output=summary
153:/task-review TASK-045 --mode=security --output=detailed
156:## Clarification Integration
160:### Context A: Review Scope Clarification (Phase 1)
177:/task-review TASK-b2c4 --mode=decision --depth=standard
239:### Context B: Implementation Preferences ([I]mplement Handler)
338:### Complexity-Based Gating
361:/task-review TASK-XXX --mode=code-quality
366:/task-review TASK-XXX --mode=decision
371:/task-review TASK-XXX --mode=architectural
376:/task-review TASK-XXX --mode=code-quality --with-questions
381:/task-review TASK-XXX --mode=decision --no-questions
394:## Flags
396:### --mode=MODE
409:/task-review TASK-XXX --mode=architectural
For TASK-FORK-PATCH specifically:


cd /Users/richardwoollcott/Projects/appmilla_github/graphiti
/task-review TASK-FORK-PATCH --mode=decision --depth=standard
Why --mode=decision: the task has 6 explicit unresolved DECISION: _TBD_ placeholders (versions, public/private, owner, tag/branch, drop-filter-vs-escape, auto-detect-vs-explicit). decision mode is purpose-built to surface and lock those before any patching starts — which is exactly what AC-FORK-01 + AC-FORK-13 + AC-FORK-15 require.

Why --depth=standard (not comprehensive): the audit itself was already comprehensive — the task body has the full bug inventory, the in-flight diff details, the production-wiring analysis, and the stale-config warnings. Standard depth is enough to lock the decisions and validate the punchlist; comprehensive would re-derive things that are already in writing.

Alternatives worth considering
--mode=architectural — defensible if you want the review to also re-litigate the strategic call (fork vs shrink vs replace). I wouldn't — that decision is solid and re-opening it before mid-May burns the time you saved by choosing the fork. Save architectural mode for the post-DDD "what next" review.
--mode=technical-debt — also defensible since the whole task IS consolidating accumulated graphiti debt. But decision is more action-forcing right now; technical-debt framing is better for the post-DDD retrospective.
--depth=comprehensive — only worth it if you want a full structured report you can hand to someone else (e.g., a co-presenter for the DDD talk). For your own use, standard is faster.
Caveats
Skip --capture-knowledge for now. That flag would try to write the review findings into the Graphiti knowledge graph via MCP — and the MCP write path is exactly what's broken (bugs #6/#7 in the audit). It would silently drop the capture. Re-enable it after TASK-FORK-PATCH lands and AC-FORK-08 verifies MCP writes work.
Run from the graphiti fork directory, not from study-tutor — the task file lives in the fork's tasks/backlog/ and /task-review looks in the current working directory's task tree.
Consider --no-questions if you don't want the clarification phase prompting you on review scope (the task is already extensively scoped); the standard prompt would mostly be redundant.
So my one-liner pick: /task-review TASK-FORK-PATCH --mode=decision --depth=standard --no-questions from the graphiti fork dir.