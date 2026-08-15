# RUNBOOK — the upload page (scans in, subjects out)

**Audience**: the operator (Rich) putting scanned study guides and notes into the
tutor's corpus.
**Status of the thing this describes**: built on branch `lane3/upload-surface`,
**not deployed anywhere and not enabled in any live container** (2026-08-14). Every
command below is a host-side command you run yourself; nothing here happens on its own.
**Built to**: [`docs/design/upload-surface-build-spec-2026-08-14.md`](../design/upload-surface-build-spec-2026-08-14.md).
**Related**: [`RUNBOOK-rag-ingest-and-smoke.md`](RUNBOOK-rag-ingest-and-smoke.md) (the
ingest and its smoke test), [`RUNBOOK-study-tutor-gb10-docker-deployment.md`](RUNBOOK-study-tutor-gb10-docker-deployment.md)
(the deploy this runbook defers to in §6).

---

## 0. What the upload page is, in one picture

Three pieces. The only thing they share is files on disk.

```
[the page]  GET /upload          [the server]  POST /api/corpus/upload      [the worker]
 plain HTML, no framework   →     runs the guards, writes the bytes    →     picks up queued jobs
 you paste the bearer into it     and a job record marked "queued"           converts them to markdown
 it holds it in memory only       and stops there — it never converts        drops them in the corpus folders
                                  and never touches ChromaDB                 runs the existing ingest
                                                                             marks the job ingested or failed
```

The server process never converts a scan and never imports docling. The worker never
serves HTTP. If the worker is not running, uploads simply sit in the queue — nothing is
lost and nothing is half-done.

Everything lands under `data/uploads/`, one directory per subject:

```
data/uploads/<subject>/
  incoming/<job_id>/<filename>   the raw file exactly as you uploaded it
  jobs/<job_id>.json             the job record (status, sha256, size, error)
  sources/                       the four-folder corpus tree the ingest reads
    primary_text/  secondary_study_guide/  secondary_critical/  context_historical/
```

---

## 1. Prerequisites (on the machine that will do the converting)

```bash
uv sync --extra ingest      # docling — turns a scan or PDF into markdown
uv sync --extra rag         # chromadb + openai — what the ingest script needs
```

`docling` is deliberately NOT in the serving image and NOT a runtime dependency: it is
only ever imported by the worker, lazily, at the moment a scan needs converting. A
checkout without the `[ingest]` extra still imports, still tests, and only complains if
you actually ask it to convert a scan — and then it tells you this command.

The embedding configuration must match the rest of the corpus, or the new subject's
vectors land in a different space from every other subject's and retrieval quietly
returns nonsense. Run the worker with the same environment the tutor runs with:

```bash
export LLM_EMBEDDINGS_BASE_URL=http://<llama-swap host>:9000/v1
export LLM_EMBEDDINGS_MODEL=embed        # 1024-dim Qwen3-Embedding-0.6B — what the spark serves
export LLM_EMBEDDINGS_API_KEY=...        # if your endpoint wants one
```

The worker prints these at startup, and **warns loudly if `LLM_EMBEDDINGS_MODEL` is
unset** — because the ingest script's own built-in default (`nomic-embed`, 768-dim) is
*not* what the deployment serves.

---

## 2. Turn the upload page on

The surface is existence-gated, exactly like voice: when the flag is not truthy the
routes are not built into the process at all — they are unknown paths (404), not
forbidden ones (403).

```bash
export STUDY_TUTOR_UPLOAD_ENABLED=1
uv run study-tutor serve-http --port 8100
```

At boot you should see:

```
event=upload_surface_wired enabled=true staging_root=data/uploads max_file_bytes=... subject_quota_bytes=...
```

Optional limits (both refused at upload time, not later):

| Variable | Default | Meaning |
|---|---|---|
| `STUDY_TUTOR_UPLOAD_ENABLED` | unset (off) | truthy ⇒ the page and the three API routes exist |
| `STUDY_TUTOR_UPLOAD_MAX_FILE_MB` | 50 | per-file cap |
| `STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB` | 500 | total staging disk per subject |

A typo in either number **fails the boot** with a named variable rather than silently
reverting to the default.

**No deployed environment sets `STUDY_TUTOR_UPLOAD_ENABLED` today.** Enabling it on the
live stack is a deploy action and is not covered by this branch (see §6).

---

## 3. The page walk

Open `http://<host>:8100/upload`. The page is served unauthenticated on purpose: it is
static HTML with no learner data in it, on a tailnet-only surface. Every API call it
makes is authenticated.

1. **Token.** Paste a bearer and press *Use this token*. **There is no operator role.**
   The three API routes resolve the caller exactly like every other route
   (`_resolve_student_id`), which accepts **any** bearer in the token table that has a
   student row — the learner's own token opens them just as well as yours. Nothing about
   these routes is privileged; what keeps them shut is that they do not exist unless you
   export the flag (§2), and that the surface is tailnet-only. Treat that as the posture,
   not as an accident to work around. The input clears
   itself; the token lives in one JavaScript variable for that tab only — not
   localStorage, not a cookie, not in the page source. Reloading the page loses it, which
   is the intended behaviour. *Forget* clears it immediately.
2. **Files.** Type the **subject** (lower-case letters/digits/hyphens/underscores,
   starting with a letter — `english`, `demo_history`). Pick the **source type** — this
   *is* the corpus folder the converted text lands in:
   - `primary_text` — the set text itself
   - `secondary_study_guide` — revision guides, study notes
   - `secondary_critical` — criticism and essays
   - `context_historical` — background and context

   Choose one or more files and press *Upload*. Files go up **one at a time, in
   sequence**, and each gets its own line in the results list: `queued (job <id>)`, or
   `refused: <plain-language reason>`. One refused scan never hides the ones that went
   through.
3. **Jobs.** The table shows file, subject, source type, status and last-updated,
   newest first, refreshing every 5 seconds while the box is ticked (or on *Refresh*). A
   failed job carries its error message as the row's tooltip. Statuses run
   `queued → converting → staged → ingested`, or `failed` with the reason.

The job table filters by whatever is in the subject box; empty it to see every subject.

---

## 4. Run the worker

The worker is host-side and runs one job at a time — ingest wants the machine to itself.

```bash
# work whatever is queued, then exit (what you want on the weekend, and in cron)
uv run python scripts/process_uploads.py --once

# or leave it polling while you scan
uv run python scripts/process_uploads.py --interval 5
```

| Flag | Default | Meaning |
|---|---|---|
| `--once` | off (loops) | one pass over the queue, then exit |
| `--interval` | 5.0 | seconds between polls when looping |
| `--staging-root` | `data/uploads` | where the jobs are |
| `--persist-dir` | `$CHROMA_PERSIST_DIR` or `data/chroma` | where the ingest writes the vectors |

For each job it: marks it `converting`; converts (`.txt`/`.md` are copied through with
the encoding normalised to UTF-8, everything else goes through docling); writes the
markdown into `sources/<source_type>/`; marks it `staged`; then runs the **existing**
ingest script for the whole subject:

```
python scripts/ingest_corpus.py --subject <subject> \
    --domain-root data/uploads/<subject>/sources \
    --collection-name gcse-<subject>-v1 \
    --persist-dir <persist dir>
```

The collection name is passed explicitly so a stray `CHROMA_COLLECTION` in your shell
cannot redirect one subject's chunks into another subject's collection. The unit of
ingest is the **subject, not the file** — the script walks the whole four-folder tree and
upserts on deterministic chunk ids, so re-running after each upload is safe and keeps the
collection agreeing with what is on disk.

Behaviour worth knowing:

- **Restart is safe.** Any job stuck in `converting` (a worker died holding it) is put
  back to `queued` at startup. Jobs already `staged` resume at the ingest step rather
  than re-converting.
- **One bad scan does not stop the pile.** Failures are written onto the job record —
  which is what the page shows you — and the worker moves on. The exit code stays 0.
- **`ingested` and `failed` are final.** Re-doing a file means uploading it again; the
  record of what happened to those bytes stays honest.
- Two uploads with the same filename do not overwrite each other — the second is written
  as `name-2.md`, with a note in the log.

After a successful run, check the vectors landed:

```bash
ls <persist dir>/.primary_text_index.<subject>     # the per-subject sidecar the tutor replays at boot
```

---

## 5. The weekend procedure, start to finish

1. On the machine with the scanner, scan each book/guide to **PDF** (one file per
   document is easiest to keep track of; multi-page PDFs are fine).
2. On the tutor host: `export STUDY_TUTOR_UPLOAD_ENABLED=1` and start `serve-http`
   (§2).
3. Open `/upload`, paste the bearer (§3).
4. Upload one subject and one source type at a time — set the subject and the radio
   button, pick that batch of files, press *Upload*, watch every file come back
   `queued`. Fix any refusal there and then (§8 says what each one means).
5. When the batch is in, run the worker: `uv run python scripts/process_uploads.py
   --once` with the tutor's embedding environment exported (§1).
6. Watch the job table go `converting → staged → ingested`. A `failed` row's tooltip
   says why.
7. Repeat 4–6 per subject / source type.
8. Sanity-check retrieval against the new store with the smoke in
   [`RUNBOOK-rag-ingest-and-smoke.md`](RUNBOOK-rag-ingest-and-smoke.md) before you
   consider the subject real.
9. **If you want the new subject in the live tutor container**, do §6 — until then it
   exists only in the store on the host.

---

## 6. Making a new subject live — the deploy-time step (stated plainly)

**Ingesting a subject does not put it in the running tutor.**

The live container's ChromaDB store is **baked into the image**: `Dockerfile:88` copies
`study-tutor/data/` into the image, and `deploy/http/docker-compose.yml` mounts only the
Hugging Face cache — there is no volume for `data/chroma`. So the container serves
whatever store was on the build host when the image was built, and a subject you ingest
today is invisible to it.

Activating a newly-ingested subject therefore requires, on the deploy host:

1. the ingest above having written into the **same** `data/chroma` the image build will
   copy;
2. an image rebuild (`./scripts/docker-build.sh`);
3. recreating the stack from the new image, per
   [`RUNBOOK-study-tutor-gb10-docker-deployment.md`](RUNBOOK-study-tutor-gb10-docker-deployment.md).

That is a deploy action. It is **out of scope for the `lane3/upload-surface` branch, has
not been done, and no part of it is automated by the upload surface.** The alternative —
mounting `data/chroma` as a volume so ingests take effect without a rebuild — is a real
option but is an undecided deployment change, not something this branch assumes.

Two housekeeping consequences of the same `COPY data/` line, worth knowing before you
build an image on a machine you have been uploading to:

- `data/uploads/` sits under `data/`, and there is **no `.dockerignore` in this repo**,
  so a staging tree full of scanned books would be copied into the image. Clear or move
  `data/uploads/` before a build.
- `data/uploads/` **is** in `.gitignore` now (added alongside `data/chroma/`), so
  `git add -A` on an upload host will not sweep scans into a commit. That closes the git
  half only — the image-build half above is still yours to do by hand.

---

## 7. What is accepted, and how much

| Guard | Value | Refusal |
|---|---|---|
| Formats | `.pdf .png .jpg .jpeg .tif .tiff .txt .md` | 400 — "Files of type … are not accepted." |
| Per-file size | 50 MB (`STUDY_TUTOR_UPLOAD_MAX_FILE_MB`) | 413 |
| Per-subject staging | 500 MB total (`STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB`) | 413 |
| Subject slug | must be a real registry slug — `^[a-z][a-z0-9_-]*$`, becoming `gcse-<subject>-v1` | 400 |
| Source type | exactly one of the four folder names | 400 |
| Filename | basename only; no traversal, no null bytes or control characters, no leading dot, ≤ 200 characters | 400 |
| **AQA assessment material** | filenames *containing* `past paper`, `mark scheme`, `examiner report` or `specimen paper` — with a space, underscore, hyphen or nothing between the words (`mark_scheme`, `pastpaper`, `specimen-paper`), any casing, anywhere in the name (widened + specimen added 2026-08-15, ruling #14) | **422 — refused, mission law 4** |
| **What that guard does NOT catch** — read this one | The check is a FILENAME check (the corpus loader's regex, imported not copied). All four of [mission law 4](../study-tutor-mission-statement-2026-08-01.md)'s categories are refused in every separator spelling since 2026-08-15 — but a paper whose name says none of those words (`june-2023.pdf`, `paper1.pdf`) sails through, and renaming is trivial. | **You are still the filter**: the guard catches accidents, not intent — check the pile by eye, and see §8 if one gets in |

Which converter handles what: `.txt`/`.md` are copied through (UTF-8 normalised, CRLF
flattened); `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff` go through docling.

The quota counts **everything** under `data/uploads/<subject>/` — the raw uploads, the
job records and the converted markdown — because all of it is disk the cap is meant to
bound. Clearing space means deleting old `incoming/<job_id>/` directories once their jobs
read `ingested` (the markdown in `sources/` is the thing the corpus needs; the raw scan
is your own archive decision).

---

## 8. Failure modes

| What you see | What it means | What to do |
|---|---|---|
| `/upload` returns 404 | `STUDY_TUTOR_UPLOAD_ENABLED` was not truthy at boot | export it and restart `serve-http` (§2) |
| API calls return 401 | no/!valid bearer — the page's token was forgotten on reload | paste the token again |
| `refused: Files of type … are not accepted` (400) | extension off the allowlist | re-export the scan as PDF |
| `refused: … looks like AQA assessment material` (422) | the filename names one of law 4's four categories in any separator spelling — mission law 4, never negotiable | do not upload it. Renaming it to something neutral *does* get it past the guard (it is a filename check, not a judge) but law 4 still forbids the material |
| A past paper, mark scheme or specimen paper went through as `queued` | its name said none of the four category terms (`june-2023.pdf`) — §7's second row: a filename check cannot catch a neutral name | before the worker runs: delete `data/uploads/<subject>/incoming/<job_id>/` and `jobs/<job_id>.json`. If it already reached `staged`/`ingested`, also delete its markdown from `data/uploads/<subject>/sources/<source_type>/` and re-run the ingest for that subject with `--reset` — plain re-ingest upserts and would leave the old chunks in the collection |
| 413 on a single file | over the per-file cap | scan at lower DPI, or split the document |
| 413 mentioning the subject's quota | the subject's staging area is full | delete ingested jobs' `incoming/` dirs, or raise `STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB` |
| 400 on the subject | slug is not registry-shaped | lower-case, start with a letter, only `a-z0-9_-` |
| Jobs stay `queued` forever | the worker is not running | run §4 |
| Job `failed`: "docling is not installed…" | `[ingest]` extra missing on this host | `uv sync --extra ingest` and re-upload |
| Job `failed`: "docling found no text…" | the scan is unreadable (dark, skewed, photo of a page) | rescan flatter and better lit |
| Job `failed`: "ingest_corpus exited …" | the ingest child failed; its last 8 lines of output are on the record | usually embeddings unreachable or the `[rag]` extra missing — check §1, then re-upload |
| Ingest ran, but the tutor answers as if the subject does not exist | the live container serves a **baked** store | §6 — this needs an image rebuild |
| Retrieval returns nonsense for the new subject only | it was ingested with a different embedding model from everything else | check `LLM_EMBEDDINGS_MODEL=embed` was exported, then re-ingest that subject |
| A job stuck in `converting` | a worker died holding it | restart the worker — it re-queues stranded jobs at startup |
| A subject's answers cite the same passage twice after a worker crash | KNOWN ISSUE: re-converting a re-queued job writes its markdown under a fresh de-collided name, so the earlier partial output is ingested TOO — duplicate chunks | before restarting a crashed worker, look in `sources/<source_type>/` for two names differing only by a `-1` style suffix and delete the older one; a code fix (clear the job's own staged outputs on requeue) is queued |
| A job file the listing skips with "Skipping malformed job file …" in the worker log | a partial write or a hand edit corrupted it | the rest of the queue keeps moving; read the named file, fix or delete it — `GET /api/corpus/jobs/{id}` on that id still shows the exact parse error (a 500 whose body names what is malformed) |

---

## 9. What this runbook does **not** claim

- Nothing here is deployed. The routes exist only when you export the flag yourself.
- **No operator privilege.** The upload routes are authed, not authorised: any seeded
  learner's bearer can write to the corpus staging tree while the flag is on (the tests
  prove it — they upload as `lilymay`). There is no operator role, group or scope in the
  token table to check, and inventing one was out of scope (the spec forbade auth changes).
  With the flag off everywhere and the surface tailnet-only this costs nothing today; it
  becomes a real decision the moment the flag goes on anywhere shared.
- **The AQA guard is a filename check, not a judge.** Since 2026-08-15 it covers all
  four of law 4's categories in every separator spelling — but a neutral filename walks
  past it, so the operator's eye remains the real gate (§7, second row).
- No multi-user tenancy: uploads are keyed by subject, not by account. The collection
  keying does not preclude ADR-ARCH-034's pilot tenancy; it does not implement it.
- The upload surface is **not** part of the frozen app contract
  (`docs/design/contracts/API-session-http-binding.md`). It is a new operator surface,
  documented here and nowhere in that contract.
- No scans have been through this pipeline yet. It was built ready for the weekend, with
  tests, not exercised on real material.
