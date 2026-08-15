# Upload Surface — binding build spec (Lane 3 step 4, overnight build 2026-08-14)

**Status:** BINDING for the `lane3/upload-surface` orchestrated build. INPUT to THE PLAN —
the Lane 3 step 4 cell is updated at close; this doc is the spec the builders execute.
**Ruling basis:** vehicle ruled 2026-08-13 (Rich: "separate page", same-origin —
`RESULTS-mac-flutter-web-boot-2026-08-13.md`); Lane 4 posture RATIFIED 2026-08-02;
ADR-ARCH-033/034 RATIFIED 2026-08-13. Scope ruled by Rich 2026-08-14 in-session:
**build it ready for upload — no uploads tonight** (scans happen this weekend);
deliverable = **branch + green tests, NOTHING deployed, NOTHING pushed**.

## What this is

A minimal same-origin web page + HTTP surface on the study-tutor app through which the
operator (Rich) uploads scanned study guides / source documents, per subject; a staging
pipeline that converts them (docling) into the **existing four-folder corpus contract**;
and the ingest trigger that lands them in the **existing per-subject ChromaDB collections**.
The page is how scans become subjects — it is the missing mouth of a pipeline whose
stomach already exists.

**Non-goals tonight:** pilot multi-user tenancy (ADR-034 — the collection keying must not
*preclude* it, that is all); deployment; enabling the surface in any live container; auth
changes of any kind; CORS (same-origin deletes the question); editing the frozen contract
(`docs/design/contracts/API-session-http-binding.md` — the upload surface is a NEW operator
surface documented here + in its runbook, never an edit there).

## Verified seams (file:line — builders build against THESE, not assumptions)

1. **Corpus contract** — `src/study_tutor/knowledge/corpus.py:82-87`
   `SOURCE_TYPE_FOLDERS`: exactly `primary_text`, `secondary_study_guide`,
   `secondary_critical`, `context_historical`. Unknown folders are skipped loudly; a
   filename-level **AQA assessment-material refusal regex** lives at ~:89-92 — REUSE it
   (import it), never duplicate it.
2. **Ingest CLI** — `scripts/ingest_corpus.py` (594 lines): `--subject` derives domain
   root, collection `gcse-<subject>-v1`, per-subject sidecar
   (`PRIMARY_TEXT_INDEX_FILENAME` + `.<subject>`); explicit `--domain-root` /
   `--collection-name` / `--persist-dir` override. Embedding function =
   OpenAI-compatible `/v1/embeddings`; code default `nomic-embed` is **NOT what the spark
   serves** — the deployment overrides `LLM_EMBEDDINGS_MODEL=embed` (1024-dim,
   Qwen3-Embedding-0.6B) via env (`deploy/http/docker-compose.yml`, load-bearing comment).
   Workers must take the model from env, never hardcode either name.
3. **Subject registry** — `src/study_tutor/cli/rag_wiring.py:90-99`:
   `SUBJECT_COLLECTION_PATTERN = ^gcse-(?P<subject>[a-z][a-z0-9_-]*)-v1$` and
   `subject_collection_name(subject)`. Upload subject slugs MUST validate against the
   subject group of this pattern.
4. **Route mounting** — `src/study_tutor/http/app.py:721-773`. The existence-gated
   pattern to copy: dev_reset at :755 (mounted only when flag set), voice at :762-766
   (mounted only when service non-None). Auth: every route resolves the caller via
   `_resolve_student_id(request)` (see dev_reset at :610) → the token-table/Keycloak
   resolver. **No static-file serving exists today** — the upload page is the first, one
   `HTMLResponse` route, no `StaticFiles` mount.
5. **Endpoint test harness pattern** — `tests/unit/http/test_student_model.py`:
   `create_app(...)` with `HTTPAuthConfig` + fake `StudentStore` + Starlette `TestClient`,
   `Authorization: Bearer test-token-student-a` fixtures. B-stage tests follow it.
6. **Docling is NOT installed** (`uv run python -c "import docling"` fails) and MUST NOT
   enter the serving image or any module under `src/study_tutor/http/` or
   `src/study_tutor/voice/`. It ships behind a NEW `[ingest]` optional-dependency group,
   imported lazily ONLY inside the docling adapter, exercised by the host-side worker CLI.
   The `[rag]` extra + `[tool.uv.sources]` CPU-torch pin in `pyproject.toml` shows the
   pattern.
7. **The live chroma store is BAKED into the serving image** (Lane 2 1a receipt) — the
   compose mounts only the HF cache. Therefore: activating a newly-ingested subject in the
   live container requires an image rebuild (or a future volume-mount decision). That is a
   DEPLOY-TIME step, named in the runbook, out of scope tonight.

## Architecture (three pieces, one contract between them)

```
[page GET /upload]        [POST /api/corpus/upload]         [worker CLI, host-side]
 static HTML+JS  ──fetch──▶ writes bytes + job.json  ──file─▶ picks up queued jobs
 bearer pasted by          under data/uploads/…              converts (docling/passthrough)
 operator, held in         status=queued                     → four-folder tree
 memory only                                                 → runs ingest_corpus --subject
                           [GET /api/corpus/jobs…]           → job status=ingested|failed
                            reads the same job files
```

The serving process NEVER converts and NEVER imports docling. The worker NEVER serves
HTTP. The contract between them is the staging tree + job files — both sides get hermetic
tests against it.

### Staging layout (the A-stage contract, everything else depends on it)

```
data/uploads/<subject>/
  incoming/<job_id>/<original_filename>     # raw uploaded bytes
  jobs/<job_id>.json                        # job record (schema below)
  sources/                                  # the four-folder tree ingest consumes
    primary_text/  secondary_study_guide/  secondary_critical/  context_historical/
```

Job record (JSON, all fields required unless noted):
`job_id` (uuid4) · `subject` · `source_type` (one of the four folder names) ·
`original_filename` (sanitised basename) · `stored_path` · `sha256` · `size_bytes` ·
`status` ∈ `queued | converting | staged | ingested | failed` · `error` (nullable) ·
`created_at` / `updated_at` (UTC ISO). Status transitions are append-style rewrites of the
file; the writer is whoever owns the transition (server: → queued; worker: everything after).

### Guards (A-stage, enforced at upload time — fail fast, not at ingest)

- extension allowlist: `.pdf .png .jpg .jpeg .tif .tiff .txt .md`
- size cap per file: 50 MB; per-subject staging quota: 500 MB (both env-overridable:
  `STUDY_TUTOR_UPLOAD_MAX_FILE_MB`, `STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB`)
- subject slug validates against the registry pattern's subject group (seam 3)
- `source_type` must be one of the four folder names verbatim
- filename passes the AQA refusal regex (seam 1) — refusal is a 422 with the reason
- filenames sanitised to basename, no traversal, no null bytes; stored under the job dir,
  never at a caller-controlled path

### HTTP surface (B-stage)

Existence-gated exactly like voice (seam 4): routes mounted only when the boot path
constructs an `UploadService` — which it does only when `STUDY_TUTOR_UPLOAD_ENABLED` is
truthy. Never enabled in any deployed env tonight.

- `GET /upload` → the page (HTMLResponse; single self-contained file, package data under
  `src/study_tutor/ingest/`, inline CSS/JS, no CDN, no framework). UNAUTHENTICATED get of
  static HTML is acceptable (tailnet-only, no data in it); every API call from it carries
  the bearer the operator pastes (kept in JS memory, never localStorage, never in the page
  source).
- `POST /api/corpus/upload` (multipart: `file`, `subject`, `source_type`) → 202
  `{job_id, status}`; guard failures → 400/413/422 with plain-language reasons.
- `GET /api/corpus/jobs?subject=` → job list; `GET /api/corpus/jobs/{job_id}` → one.
- All three API routes resolve the caller via `_resolve_student_id` — same as every route.
- ERROR SHAPE follows the binding's §4 conventions (validation → 400, no error_type) —
  copy the neighbours, invent nothing.

### Converter port + worker (C-stage)

- `Converter` Protocol in `src/study_tutor/ingest/converter.py`:
  `convert(src: Path, dst_dir: Path) -> ConversionResult` (markdown files out; result
  carries produced paths + per-file notes). Implementations:
  - `PassthroughConverter` (`.txt`/`.md` — copy through, normalise encoding to UTF-8);
  - `DoclingConverter` in `converter_docling.py` — lazy `import docling` inside the
    method; raising a clear "install the [ingest] extra" error when absent.
- Worker CLI `scripts/process_uploads.py`: scan `data/uploads/*/jobs/*.json` for
  `queued` → converting → write converted markdown into
  `sources/<source_type>/` → staged → invoke the ingest (import `scripts/ingest_corpus.py`
  main, or subprocess it) with `--subject <subject> --domain-root
  data/uploads/<subject>/sources` and env-driven embedding config → ingested; any
  exception → failed + error message. One job at a time; idempotent on restart
  (converting-state jobs are re-queued on startup). `--once` flag for tests/cron;
  default loops with a sleep interval.
- VERIFY during build (do not assume): where `ingest_corpus.py` writes the per-subject
  sidecar and that `rag_wiring` subject discovery would find the resulting collection —
  pin both with a test.
- `[ingest]` extra added to `pyproject.toml` with docling pinned to a tested version.
  If the docling install fails in the overnight environment, the stage still passes with
  `DoclingConverter` built + unit-tested via mocked docling module — record the install
  failure honestly in the stage summary; do NOT fake a green install.

### Second-subject seam proof (D-stage — INDEPENDENT of A/B/C, exercises EXISTING code)

Prove the multi-subject plumbing carries a genuine second subject, hermetically:
- build a tiny fixture corpus (crafted public-domain-safe text, ~20 paragraphs) in a TEMP
  dir in four-folder shape, subject `demo_history`;
- run the REAL `scripts/ingest_corpus.py` against it with a STUB embedding function and a
  TEMP `--persist-dir` (never the repo's `data/chroma` — that directory is baked into the
  next image build; polluting it ships a demo corpus to production);
- assert: collection `gcse-demo_history-v1` exists with expected chunk count + metadata;
  `rag_wiring` subject discovery parses it; the sidecar lands where discovery reads it;
- assert the english store is untouched (581 chunks in `gcse-english-v1`, count pinned
  read-only);
- land the whole proof as a repeatable pytest module (marker: hermetic — no network, no
  llama-swap, no Postgres, no docker).

### Runbook + closes (E-stage)

`docs/runbooks/RUNBOOK-upload-surface.md`: enable flag, page walk, worker invocation,
the weekend scan→upload→ingest procedure start-to-finish, the DEPLOY-TIME activation
step (baked-store rebuild — seam 7) stated honestly, quota/format table, failure modes.
Update THE PLAN's Lane 3 step 4 cell (state what exists, what is NOT deployed, the named
activation step). README of `src/study_tutor/ingest/` explaining the three-piece
architecture in ten lines. Claims only what the code does.

## Fences (every stage, verbatim in every prompt)

- NEVER push, deploy, docker build/run/stop, or touch `deploy/http/.env*` or any live
  container/env. The deliverable is a branch.
- BROKER ISOLATION (standing): no NATS — no `nats://`, no `:4222`, no client imports
  outside mocks. Coaches grep the diff for it.
- No live-shaped credential (`st_` + 30 chars) anywhere; no retired bearer names;
  `tests/test_no_live_credentials.py` must stay green — it scans the WHOLE repo.
- No docling import outside `converter_docling.py` + its tests; nothing under
  `src/study_tutor/http/` may import from `converter_docling`.
- No edit to `docs/design/contracts/API-session-http-binding.md`, no edit to existing
  routes' behaviour, no edit to `app/**` (Flutter), no edit to `.env.example` beyond an
  additive upload block.
- Path-limited local commits on the stage's own files; hermetic suite
  (`uv run pytest -m "not integration and not live and not keycloak" -q`) green before
  every commit — and if a stale `guardkit-test-pg-session-svc` container makes the
  settlement file error with docker exit 125, `docker rm -f guardkit-test-pg-session-svc`
  IS permitted (it is a leaked TEST container, not a live surface — the one docker
  command allowed).
- Plain-language naming (playbook amendment 7): the surface is called the **upload page /
  upload surface** everywhere user-facing; no new codenames.
```
