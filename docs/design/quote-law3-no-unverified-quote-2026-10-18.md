# Design — law 3 holds in every session: an unmatched quote is removed, and sessions with no set text still verify

2026-10-18 · Rich's instruction (18 Oct): work the remaining items with `cross-model-build`. Mission law 3
(`docs/study-tutor-mission-statement-2026-08-01.md`): "**Never an unverified quote.** Anything presented as
quotation is verified against the corpus before the student sees or hears it; no corpus ⇒ analysis mode, not
confident fabrication."

## The incident

18 Oct 2026, Dell :8100, the Reachy robot's session (started with `{"subject": "english", "resume_if_active": true}`,
no topic). Every turn logged `event=orchestrator_turn_completed text_name= retrieval_mode=skipped reason=no_text_name`.
A reply delivered to the learner contained a fabricated Macbeth "quotation": *"perhaps I have no spur / To prick the
sides of my intent, but only / Remorse, that when this deed is done, / Makes ne'er so much the trống than makes me thus
a backwardly"*. The async Coach scored it 0.15 afterwards — too late (production Coach is async; it only flags).

## Why law 3 failed (receipts)

**L1 — no set text ⇒ the verifier runs against nothing.** `text_name` is set once at start by
`derive_text_name` (`gamification/texts.py:204-238`) from keyword matching on the request topic, the planner topic
or the subject; the robot (and the phone's default "planner pick" start) send no topic, and the planner's fallback
topics ("introductory diagnostic", curriculum defaults) name no text ⇒ `None`. The handover closure
(`cli/main.py:167-175`) and the streaming verifier factory (`cli/main.py:269-271, 294-300`) then call the verifier with
no chunks and an empty text name.

**L2 — an unmatched quote is softened, not removed.** For a `NoMatch`, `quote_verifier.py` keeps the span's words
(`:603-607`, "span content kept"), strips only the quote marks and inserts "perhaps " (`:547-556`). On the voice path
quote marks are inaudible, so the fabricated line is *heard* exactly as invented. The incident's delivered text shows
this branch ran: it reads "he says **perhaps** I have no spur / …" — the inserted "perhaps", with the invented words kept. This applies to sessions **with** a
set text too, for any fabricated quote (the incident's line is far beyond the fuzzy-match distance from any real line).

## The fix (two parts, both server-side; no contract change)

### Q1 — remove unverifiable quotes (law 3 in every session)

`verify_quotes` / `apply_quote_verification` gain a keyword `redact_unmatched: bool = False`. When true, a `NoMatch`
span (the quote marks and everything between them) is replaced by the fixed neutral text
`UNVERIFIED_QUOTE_TEXT = "a line I'd want you to check in your own copy of the text"`, with no "perhaps". The
`NoMatchStrip` record gains `redacted: bool = False` (additive, defaulted). Both production call sites (the non-streaming
handover closure and the streaming per-turn verifier factory in `cli/main.py`) pass `redact_unmatched=True` **always**:
law 3 makes no exception for sessions that have a set text. The default `False` keeps the verifier's existing unit
contract for any other caller. The streaming path's "released text never changes" invariant
(`orchestrator.py:902-912`) holds because the replacement happens inside a closed quote before release, exactly where
today's strip happens.

Accepted cost: a genuine line that retrieval did not surface in its top chunks is also removed. That is the safe side of
law 3 ("verified … before the student sees or hears it").

### Q2 — no set text ⇒ verify against all of the subject's primary texts

So that Q1 does not make every quote impossible in robot sessions and default phone sessions:

* `retrieval.retrieve(..., text_name: str | None)` accepts `None`; `_query_collection` then omits the text-name filter
  but keeps the primary-text source-type filter. Collections are per subject, so this is "all primary texts of this
  subject", never another subject.
* `should_retrieve(text_name=None, …)` retrieves when the subject has any primary text registered (new helper
  `primary_texts_for(subject)`); the AO3-only and embedder-timeout skips are unchanged.
* `quote_verifier.verify_quote`: when the session text name is empty, every primary chunk is in scope for exact and
  fuzzy matching and the cross-text branch is off (no text is "the session's" text). Citations come from the matched
  chunk, so they stay correct.
* `cli/main.py` (both sites): when `text_name` is empty, retrieve with `text_name=None` and log
  `scope=all_primary_texts reason=no_text_name` instead of skipping.

Cost: one Chroma query per turn, the same as a session with a set text (it already overlaps generation on the
streaming path).

### Not chosen

* **Defaulting a `text_name` at start**: `text_name` drives which text a session's achievements credit
  (`knowledge/store/postgres.py:371-406`), so a guess would mis-credit the learner, and pinning one text turns real quotes
  from the other two into cross-text paraphrases.
* **Robot sending a topic**: optional and later; the server must not depend on it.

### Out of scope, recorded

* `extract_quotes` only sees double quotes (`quote_verifier.py:265`); British single quotes (‘…’) and unquoted verse
  with " / " are never checked, in any session. Fixing it touches `voice/verified_stream.py` too and apostrophes make it
  delicate — a separate change.
* The Coach's `quote_fidelity` reading of a redacted span is unchanged (the Coach sees the post-verification text).

## Acceptance

* Hermetic suite green.
* New tests: (1) `redact_unmatched=True` removes the span, inserts the neutral text, sets `redacted=True`, no
  "perhaps"; (2) flag off ⇒ unchanged (existing tests stay green); (3) empty session text ⇒ an exact Macbeth match is a
  primary match with its chunk's citation, no cross-text event; fuzzy works across all texts; (4)
  `should_retrieve(None, …)` retrieves when the subject has primary texts and skips with the no-primary reason otherwise,
  AO3-only skip intact; (5) `retrieve(text_name=None)` builds no text-name filter, an unwired subject returns `[]`;
  (6) both `cli/main.py` sites with no `text_name`: the fake collection is queried without a text filter, a real quote
  survives, the incident's fabricated line is replaced, the scope log line appears; (7) `run_turn_stream_verified` with a
  no-text session never releases the fabricated line in any chunk nor hands it to the Coach; (8) a regression test using
  the incident's reply text.
* Runtime on the Dell after deploy: a robot-shaped session (subject only) logs `scope=all_primary_texts`, and a prompt
  that elicits a misquotation produces the neutral text, not the invented line.
