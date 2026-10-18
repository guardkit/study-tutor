# Design — a refused turn must not break the session; "the tutor is busy" instead of a bare 500

2026-10-18 · Rich's instruction (18 Oct): "proceed with your recommendations" — options (a) and (b) from
ai-transition `docs/handoffs/study-tutor-models-brief-2026-10-18.md` ("Known problems" 1, 2 and 4).
Built Claude-led under `cross-model-build`, Codex reviewing.

## The defects, with receipts

Live tests on the Dell, 17 October (`~/factory-live/review-evidence/2026-10-17-*` on the Dell), and the two
app containers' logs for the 48 hours before 18 Oct 10:00 UTC:

| Upstream answer from llama-swap (:9000) | Count (8100 / 8101) | Meaning |
| --- | --- | --- |
| `502 Bad Gateway` | 18 / 0 | `mem-check` refused to load `gemma4-tutor` (the Dell's memory floor or the factory model's start hold) |
| `429 Too Many Requests` | 0 / 7 | the tutor model was already serving (`-np 1`, `concurrencyLimit: 2`) |
| `400 Bad Request` | 10 / 14 | the Gemma chat template's `raise_exception("Conversation roles must alternate …")` |

**D1 — one failed turn poisons the rest of the session.** `SessionService.turn` / `turn_stream`
(`src/study_tutor/session/service.py`) persist the learner's row *before* generating and persist no tutor row
when generation fails. The next turn's `build_turn_session_state` drops only the *trailing* user row, so the
prior window now ends with the orphaned learner row, and `LLMClient` appends the new learner message after
it: two `user` messages in a row. The template (`/opt/llama-swap/config/gemma4-tutor.jinja`) requires the
messages after the system prompt to be strictly `user, assistant, user, …` starting with `user`, so every later
turn is refused with a 400 in under 10 ms. Durable rows stay orphaned, so the session never recovers.

**D2 — the window can start with a tutor turn.** `_build_transcript_history`
(`src/study_tutor/tutoring/adapters/llm_player_adapter.py`) enforces the 1,500-token cap by dropping the oldest
*single* turn until the window fits. An odd number of drops leaves the history starting with `assistant`, which
the same template rejects. Same symptom, no failure needed: just a long-enough conversation.

**D3 — a refused or busy model shows the learner a bare HTTP 500.** `LLMClient` raises `LLMProviderError`
(status lost except in the chained cause); the HTTP/WS/voice boundaries treat it as an unexpected error →
`500 {"error": "Internal server error"}`, and the app shows its generic connection-problem treatment.

## The fix

### F1 — the Player's history is always well-formed (fixes D1 and D2)

In `_build_transcript_history` only, before windowing:

1. **Pair the transcript.** Walk the prior turns oldest → newest and keep only complete
   `(user, tutor)` pairs: a `user` row immediately followed by a `tutor` row. An unanswered `user` row (followed
   by another `user` row, or last in the prior window) and a `tutor` row without a preceding `user` row are
   left out of the model's context.
2. **Window by whole pairs.** Keep the last `_TRANSCRIPT_WINDOW_TURNS // 2` pairs (6), then drop the oldest
   *pair* while the summed characters exceed the cap. The newest pair is always kept, even over budget (today's
   "a single over-budget final turn is kept" rule, applied to the pair).

The result is always `user, assistant, …, assistant`, so with the current learner message appended the
template's rule holds. **Durable rows are not changed**: the transcript the learner and Rich see still shows
the unanswered message, and **sessions already poisoned heal on their next turn** with no data repair. The
change is at the model boundary, where the template constraint lives, so the HTTP, WS and voice paths all get
it (they share `respond` / `respond_stream`).

Not chosen: deleting the learner's row on failure (the phone mirror has already shown it; losing what a learner
said is worse than leaving it unanswered) and merging consecutive learner rows (the model would answer a stale
question the learner has moved past).

### F2 — a busy or refused tutor model is a typed, learner-safe error (fixes D3)

1. `LLMProviderError` gains `status_code: int | None`, set from the `httpx.HTTPStatusError` response in both
   `_generate_openai_compat` and `_generate_stream_openai_compat` (`None` for connection errors etc.). Message
   text unchanged.
2. New session error `TutorBusy(SessionServiceError)` in `session/errors.py`. `SessionService.turn` and
   `turn_stream` raise it when the reply raises `LLMProviderError` with `status_code in {429, 502, 503}`
   (chained, logged at WARNING with the upstream status). Any other failure is unchanged. For `turn_stream`, the
   existing in-band error event carries `error_type="TutorBusy"` instead of `"generation_failed"`, and the socket
   stays open — it is not a terminal error, the learner can send again.
3. Transport mapping, every place a reply is generated:
   * `POST …/turn` and `POST …/voice-turn` → `503` with
     `{"error": "The tutor is busy right now. Please try again in a minute.", "error_type": "TutorBusy"}` and
     `Retry-After: 30`.
   * WS text and voice turns → the error frame `{type: "error", error, error_type: "TutorBusy"}`; socket kept open.
4. **Contract — additive.** `docs/design/contracts/API-session-http-binding.md` §4.1 gains one row
   (`TutorBusy` · 503 · upstream tutor model busy or refused to load), marked *(Rev 2, additive)*. Already-installed
   apps map an unknown `error_type` to `TransportError` → the connection-problem treatment they show today for the
   500, so no installed client gets worse. The app side (a `TutorBusy` exception, both adapters' mappings, and the
   "busy" copy) is a separate small change made and tested on the Mac with `flutter test`; this server change does
   not depend on it.

### F3 — the tutor model serves two conversations at once (option a; Dell config, not code)

In the Dell's `/opt/llama-swap/config/config.yaml` stanza `gemma4-tutor`, after a dated backup:
`-np 1` → `-np 2`, `--ctx-size 16384` unchanged (two 8K slots), `concurrencyLimit: 2` → `3` (two served, one
waiting, the fourth refused with 429 → `TutorBusy`). 8K per conversation is about 4× the largest request
measured on 17 October (1,976 tokens at turn 26, the tutor model's own log); the history cap is 1,500 tokens. KV
memory is set by the total context, so it is unchanged; compute buffers grow slightly — measured after reload
against `mem-check`'s 18 GiB planning figure. The factory's model, LiteLLM and the factory router are not
touched.

## Acceptance

* Hermetic suite green: `uv run pytest -m "not integration and not live and not keycloak" -q`.
* New unit tests: the paired history for (a) an orphaned learner row before the current one, (b) several
  consecutive orphans, (c) a leading tutor row, (d) a token cap forcing an odd number of single-turn drops under
  the old rule, (e) a single over-budget newest pair; each asserts the strict alternation the template enforces.
* New tests: `LLMProviderError.status_code` from both client paths; service raises `TutorBusy` for 429/502/503 and
  not for 400/500/connection errors; `/turn` and `/voice-turn` return 503 + envelope + `Retry-After`; WS emits the
  `TutorBusy` frame and keeps the socket open.
* Runtime on the Dell after deploy (F3 config + rebuilt images): a session with an orphaned learner row answers
  its next turn; two concurrent learners are both answered; a third/fourth concurrent request gets `TutorBusy`.
