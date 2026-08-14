# `study_tutor.ingest` — the upload page's machinery

Three pieces, and the only thing they share is files on disk:

1. **The server side.** `guards.py` + `staging.py` + `jobs.py` + `config.py`: an upload is
   checked (subject, source type, filename, format, size, quota, AQA refusal), its bytes are
   written under `data/uploads/<subject>/incoming/<job_id>/`, and a `queued` job record is
   written beside it. That is all the serving process ever does — it never converts.
2. **The page.** `upload_page.html`, one self-contained file with no framework and no CDN,
   served by `study_tutor.http.app` at `GET /upload` when `STUDY_TUTOR_UPLOAD_ENABLED` is set.
3. **The worker side.** `converter.py` (the port) and `converter_docling.py` (the only module
   in the repo allowed to import docling, lazily): the host-side `scripts/process_uploads.py`
   turns queued jobs into markdown in `sources/<source_type>/` and runs the existing
   `scripts/ingest_corpus.py`, moving each job to `ingested` or `failed`.

Because the contract is files, both sides are testable without each other — no HTTP, no
docling, no broker, no network anywhere in this package. Operator instructions:
[`docs/runbooks/RUNBOOK-upload-surface.md`](../../../docs/runbooks/RUNBOOK-upload-surface.md).
