---
id: TASK-NATS-PH3-006
title: "Bug #5: Dockerfile missing COPY for roles/, data/, and .guardkit/graphiti.yaml (runtime asset gap)"
status: completed
task_type: bugfix
implementation_mode: task-work
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
feature_slug: nats-fleet-integration
wave: 10
priority: critical
created: 2026-05-10T21:00:00Z
updated: 2026-05-10T23:05:00Z
completed: 2026-05-10T23:05:00Z
completed_location: tasks/completed/TASK-NATS-PH3-006/
complexity: 3
estimated_minutes: 45
actual_minutes: 35
tags:
  - nats
  - docker
  - phase-3
  - bug-5
  - demo-blocker
  - dddsw-2026
dependencies:
  - TASK-NATS-PH3-001
related_tasks:
  - TASK-NATS-PH3-002
  - TASK-NATS-PH3-003
blocks:
  - TASK-NATS-PH3-005
source: docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md
evidence: docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log
patch_status: committed
commit: e92827c
test_results:
  status: passed
  passed: 6
  failed: 0
  coverage: structural-only-by-design
  last_run: 2026-05-10T22:55:00Z
  test_file: tests/unit/test_dockerfile_assets.py
---

# Task: Bug #5 — Dockerfile does not COPY runtime assets into the image

## Description

`study-tutor/Dockerfile` ships only application code (`src/`, `pyproject.toml`,
`uv.lock`). Three runtime asset trees are absent from the image:

| Missing path in image | Required by |
|---|---|
| `/workspace/study-tutor/roles/tutor/role.yaml` | Role-manifest loader (`cli/main.py:491`) |
| `/workspace/study-tutor/data/` | Data-layer bootstrap |
| `/workspace/study-tutor/.guardkit/graphiti.yaml` | Graphiti-config loader (`cli/main.py:502`) |

Both loaders are configured to **refuse silent fall-back to defaults**
(DECISION-DF-001 / AC-LOAD-06), so the container crash-loops before it
ever reaches its NATS connect. Surfaced during the 2026-05-10 dress-rehearsal
run of `RUNBOOK-study-tutor-nats-fleet-demo.md` at commit `82f2aba`.

### Symptoms (from the 2026-05-10 run, in order of appearance)

First crash (pre-patch):
```
FileNotFoundError: Role manifest not found:
/workspace/study-tutor/roles/tutor/role.yaml.
Ensure the bash wrapper cd's to the absolute repo root (SR-02).
```

After adding `roles/` + `data/` COPY, second crash:
```
FileNotFoundError: graphiti config not found at .guardkit/graphiti.yaml.
Refusing to silently fall back to defaults — see DECISION-DF-001 / AC-LOAD-06.
Run from the project root or pass an explicit path.
```

Both surface from `_build_nats_runtime` at boot; the agent never reaches
its NATS connect on either attempt.

### Root cause

`Dockerfile` at `82f2aba` contains:
```dockerfile
COPY study-tutor/pyproject.toml study-tutor/uv.lock ./
COPY study-tutor/src/ ./src/
```

`roles/`, `data/`, and `.guardkit/graphiti.yaml` are runtime assets required
at boot but never shipped into the image.

## Patch already applied (uncommitted)

**The fix was applied in-tree during the 2026-05-10 runbook execution and is
sitting as an uncommitted working-tree change.** Whoever picks this task up
should verify the three COPY lines are present in `Dockerfile` (after the
`src/` copy), confirm the image builds and boots cleanly, add the regression
test (see Acceptance Criteria #3), and commit the whole lot together.

The three lines added during that session:
```dockerfile
COPY study-tutor/roles/ ./roles/
COPY study-tutor/data/ ./data/
COPY study-tutor/.guardkit/graphiti.yaml ./.guardkit/graphiti.yaml
```

These appear immediately after `COPY study-tutor/src/ ./src/` in the
Dockerfile.

## Scope

1. Verify (or re-apply) the three COPY lines in `study-tutor/Dockerfile`.
2. Rebuild the image: `scripts/docker-build.sh` (or the equivalent BuildKit
   command) and confirm `docker run --rm --entrypoint sh study-tutor:dev -c 'ls /workspace/study-tutor/'`
   shows `roles/`, `data/`, and `.guardkit/`.
3. Add a regression unit test (sibling to
   `tests/unit/test_compose_structure.py`) that asserts the three asset paths
   exist inside the built image — so the gap cannot reappear silently.
4. Commit `Dockerfile` + the new test in a single commit attributed to
   `fix(FEAT-NATS): ship roles/data/.guardkit assets into Docker image (Bug #5)`.

## Acceptance criteria

- [ ] Built image contains `/workspace/study-tutor/roles/tutor/role.yaml`
      (verifiable with
      `docker run --rm --entrypoint sh study-tutor:dev -c 'cat /workspace/study-tutor/roles/tutor/role.yaml'`).
- [ ] Built image contains `/workspace/study-tutor/data/` directory
      (verifiable with
      `docker run --rm --entrypoint sh study-tutor:dev -c 'ls /workspace/study-tutor/data/'`).
- [ ] Built image contains `/workspace/study-tutor/.guardkit/graphiti.yaml`
      (verifiable with
      `docker run --rm --entrypoint sh study-tutor:dev -c 'cat /workspace/study-tutor/.guardkit/graphiti.yaml'`).
- [ ] `docker compose -f docker-compose.study-tutor.yml up -d` reaches
      `NATSAdapter ready for agent 'gcse-tutor'` without any crash-loop on
      the role-manifest or graphiti-config loaders (i.e. Phase 1.1 of the
      runbook passes on the first attempt).
- [ ] A new unit test file (e.g. `tests/unit/test_dockerfile_assets.py`,
      sibling to `tests/unit/test_compose_structure.py`) asserts that the
      three asset paths are present in the built image. The test must be
      discoverable by the project test runner and must pass in CI.
- [ ] All modified files pass project-configured lint/format checks with zero
      errors.
- [ ] `Dockerfile` cache layering is preserved: `uv sync` (deps) must remain
      cached across rebuilds that touch only `src/`, `roles/`, `data/`, or
      `.guardkit/graphiti.yaml` — do not move the `COPY pyproject.toml uv.lock`
      layer.

## Implementation notes

- Recommended approach is **Option A** from the runbook Bug #5 analysis:
  bake the assets into the image via COPY. Option B (bind-mount) is
  explicitly rejected — it couples the image to the host layout and breaks
  the "ships under the same operational shape" demo goal. Option C
  (`importlib.resources`) is the right long-term fix but is out of scope here.
- The WORKDIR inside the image is `/workspace/study-tutor`; the BuildKit
  context root is the repo parent, so Dockerfile source paths are
  `study-tutor/roles/`, `study-tutor/data/`, and
  `study-tutor/.guardkit/graphiti.yaml`.
- `.guardkit/graphiti.yaml` is a single file, not a directory; COPY it
  explicitly to avoid accidentally shipping the rest of `.guardkit/` into the
  image.
- The regression test for AC #5 may need to invoke `docker run` or inspect a
  pre-built tarball. Follow the pattern already established in
  `tests/unit/test_compose_structure.py` for how this project tests container
  artefacts. If the project has no existing pattern for image-content
  inspection, a subprocess-based test that calls `docker run --rm --entrypoint sh`
  is acceptable.
- Demo deadline: **2026-05-16 (DDDSW)**. This is a demo-blocker — without
  this fix the container does not boot and Phase 1 of the runbook cannot
  complete.

## Coach validation

```bash
# Confirm patch is in place
grep -c 'COPY study-tutor/roles/' Dockerfile
grep -c 'COPY study-tutor/data/' Dockerfile
grep -c 'COPY study-tutor/.guardkit/graphiti.yaml' Dockerfile

# Rebuild
scripts/docker-build.sh

# Verify assets present in image
docker run --rm --entrypoint sh study-tutor:dev -c \
    'ls /workspace/study-tutor/roles/tutor/role.yaml \
         /workspace/study-tutor/data/ \
         /workspace/study-tutor/.guardkit/graphiti.yaml'

# Smoke boot (requires NATS up + RICH_NATS_PASSWORD set)
docker compose -f docker-compose.study-tutor.yml up -d
sleep 15
docker compose -f docker-compose.study-tutor.yml logs --tail=30 | grep -E 'ready|Error|FileNotFound'
docker compose -f docker-compose.study-tutor.yml down
```

## Completion record (2026-05-10)

Committed as `e92827c` on `main`. Acceptance status:

| AC | Status | Evidence |
|---|---|---|
| #1 `roles/tutor/role.yaml` in image | ✅ verified | `docker run --rm --entrypoint sh study-tutor:dev -c 'ls /workspace/study-tutor/roles/tutor/role.yaml'` returned the 340-byte manifest (role.id=tutor). |
| #2 `data/` directory in image | ✅ verified | `docker run` listed `chroma/` under `/workspace/study-tutor/data/`. |
| #3 `.guardkit/graphiti.yaml` in image | ✅ verified | `docker run` returned the 1551-byte falkordb config (whitestocks:6379). |
| #4 compose smoke reaches "NATSAdapter ready" | ⏸️ deferred to runbook | Requires a running NATS broker + `RICH_NATS_PASSWORD`; pre-conditions (asset gap) are now resolved so Phase 1.1 of `RUNBOOK-study-tutor-nats-fleet-demo.md` can pass on the next attempt. |
| #5 regression test discoverable + passes | ✅ verified | `tests/unit/test_dockerfile_assets.py` — 6 tests, all passing. |
| #6 lint/format clean | ✅ verified | `uv run ruff check` and `uv run ruff format --check` both clean on the new file. |
| #7 deps-layer cache preserved | ✅ verified | The rebuild against `study-tutor:dev` showed the `pyproject.toml uv.lock` COPY and the `uv sync --no-install-project` layer as `CACHED`; my new COPYs sit inside Layer 2 and do not bust the deps layer. `test_lockfile_copy_precedes_asset_copies` pins this invariant. |

### Out-of-scope drift left in the working tree

The 2026-05-10 runbook session also produced uncommitted changes to
`docker-compose.study-tutor.yml` and `tests/unit/test_compose_structure.py`
(Bug #6 — Coach model env vars). Those belong to TASK-NATS-PH3-007 and
were deliberately NOT staged into this commit — they will be picked up
by `/task-work TASK-NATS-PH3-007`.

### Pre-existing test failures noted (NOT introduced by this task)

`tests/unit/test_dockerfile_structure.py` has 3 pre-existing failures
where a brittle `re.findall(r"uv sync[^\n]*", ...)` regex matches the
literal text `uv sync` inside a docstring comment at line 49 of
`Dockerfile` (`# git, and without it the Layer 1 ``uv sync`` below
fails with`). Verified by stashing the Dockerfile patch and re-running:
the three failures reproduce against HEAD's Dockerfile too. Out of
scope for this task; should be filed as a follow-up bug against
TASK-NATS-PH3-001's regression tests.
