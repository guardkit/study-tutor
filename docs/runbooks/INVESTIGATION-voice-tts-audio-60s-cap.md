# Investigation — voice replies get their spoken audio cut off (~60s cap)

**For:** the study-tutor session on **spark** · **From:** the MacBook/app leg · **Date:** 2026-07-26
**Status:** **RESOLVED 2026-07-26 — Option A implemented (v3: serial chunked synthesis,
piece cap 2, TTL-deferred storage), deployed on spark `:8100`, final E2E PASS.** See
the Resolution section at the end. **No app change needed** (confirmed again in the wild:
multi-chunk `audio[]` played as designed).

---

## TL;DR

Long tutor replies play back with the **end of the spoken answer missing**. The full text renders on screen; only the *audio* is short. The cause is **`qwen3-tts-0.6b` capping its own generation at ~60 s (~170–180 words)** per synthesis call. The study-tutor server sends the whole reply to TTS and the Flutter app plays every chunk it's given — neither truncates. The clean fix is to **synthesize the reply in sentence/paragraph pieces and return them as multiple `audio[]` chunks** (the app already plays a multi-chunk `audio[]` as one continuous answer, so this is server-only).

---

## Symptom

During the first live tap-to-talk on the phone (table-mode against spark `:8100`, signed in as `alex`), a spoken question produced a correct transcript, the tutor's full text reply on screen, and audio playback — but the operator reported the **spoken answer "cut a little short."** It happened on a long, multi-paragraph reply.

## Investigation (how it was isolated)

Worked outward from the client, ruling out each layer:

**1. Ruled out the app.** The Flutter client places no cap on playback and plays *all* audio chunks to completion:
- `HttpVoiceApi.voiceTurn` spreads **every** entry of the response `audio[]` array into an `AudioAnswerPart` — no `.first`/`.take` (`app/lib/adapters/http_voice_api.dart:125-136`).
- `_playAnswer` selects all audio parts, sorts by `seq` ascending, fetches each chunk, then plays the full list (`app/lib/ui/session_screen.dart:468-480`).
- `JustAudioPlayback.playSequential` loops the chunks, `await`-ing each to end-of-file before the next, so they're heard back-to-back as one utterance (`app/lib/adapters/audio_playback.dart:37-53`).

**2. Ruled out the study-tutor server text.** `voice_turn` passes the **complete** `tutor_response` to TTS with no truncation:
- `AudioClient.synthesize(tutor_response, response_format="wav")` sends `input: text` verbatim (`src/study_tutor/voice/client.py`, `service.py:316-317`).

**3. Measured the TTS model directly** (POST `/v1/audio/speech`, model `qwen3-tts-0.6b`, voice `Ryan`) and compared audio duration to input length:

| Input text | Words | Expected @ ~2.9 wps | **Actual audio** | Result |
|---|---|---|---|---|
| Real tutor reply (metaphor) | 182 | ~63 s | **62.88 s** | full — right at the edge |
| Varied prose passage | 242 | ~83 s | **58.96 s** | **truncated ~30 %** (tail dropped) |
| Repetitive sentence ×24 | 528 | ~182 s | 34.96 s | confounded (TTS models emit an early end-of-speech on looping text — *not* a clean cap signal, noted for honesty) |

The varied-prose case is the clean one: 242 words of ordinary prose yielded only **58.96 s** where ~83 s was due, stopping near a sentence boundary. Combined with the 182-word reply rendering fully at 62.88 s, the effective ceiling is **~60 s / ~170–180 words per synthesis call.**

## Root cause

**`qwen3-tts-0.6b` (the TTS model on spark's `:9000` llama-swap) caps its output at ~60 s.** For any single `synthesize()` call whose text exceeds ~170–180 words, the model stops mid-reply and returns audio only for the first ~60 s. The study-tutor server currently makes **one** synthesis call for the **whole** reply (`service.py:316-325`), so a long reply loses its tail.

## Reproduce it yourself (from spark)

```bash
# ~240 words of varied prose -> expect ~83s if uncapped
curl -s -X POST "http://127.0.0.1:9000/v1/audio/speech" -H "Content-Type: application/json" \
  -d '{"model":"qwen3-tts-0.6b","voice":"Ryan","input":"<paste ~240 words of varied prose>","response_format":"wav"}' \
  -o /tmp/long.wav
# duration comes back ~59s, not ~83s:
ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 /tmp/long.wav   # or: afinfo /tmp/long.wav
```

A short input (<~170 words) renders in full; a long one clips at ~60 s. That's the whole diagnosis in one command.

---

## Options (your call)

### Option A — Chunk the reply server-side (recommended; app already supports it)
Split `tutor_response` into sentence/paragraph-sized pieces, synthesize each as its own chunk, and return them as the `audio: []` array with **ascending, contiguous `seq`**. The app plays them as one continuous answer with no change.

**Exact change site** — `VoiceTurnService.voice_turn`, `src/study_tutor/voice/service.py`:
- Today (`service.py:314-325`): one synth + one ref —
  ```python
  audio_refs: list[AudioRef] = []
  try:
      audio_bytes = await self._audio_client.synthesize(tutor_response, response_format="wav")
      chunk_id = self._chunk_store.put(session_id, audio_bytes)
      url = f"/api/sessions/{session_id}/voice-audio/{chunk_id}"
      audio_refs = [AudioRef(seq=0, chunk_id=chunk_id, url=url)]
  except VoiceUnavailable as e:
      ...  # ASSUM-005: text-only, audio_refs stays []
  ```
- Change to: split → synth each piece → store each → append an `AudioRef(seq=i, …)` per piece (i = 0,1,2,…). `AudioRef` (`service.py:46`) already carries `seq`; the return at `service.py:339-342` (`audio=audio_refs`) is unchanged. Sentence-splitting is a small pure helper (regex on `.?!` boundaries, then coalesce so each piece stays comfortably under the ~60 s / ~150-word ceiling — leave headroom).

**Constraints to respect:**
- **Per-synthesis timeout** — each `synthesize()` gets `audio_timeout_seconds` (`config.py`); shorter pieces each synthesize *faster*, so this gets safer, not riskier. Total wall-clock is the sum of pieces — keep the piece count modest (a few, not dozens).
- **ASSUM-005 (TTS-fail ⇒ text-only)** — decide the partial-failure policy: if piece *k* raises `VoiceUnavailable`, either return the pieces synthesized so far (partial audio + rest as text) or fall back to `audio=[]`. Pick one and document it; the app tolerates any-length `audio[]` including empty.
- **Ephemeral-audio invariant** — keep storing each piece in the in-memory TTL `ChunkStore` and discarding raw bytes; do not write audio to disk/DB/logs. `ChunkStore` TTL is 120 s and evicts by `max_entries` — a handful of chunks per turn is well within it.
- **Each chunk must be an independently decodable audio file** — the app writes each chunk to a temp file and `setFilePath`s it (`audio_playback.dart:42-44`). Split on **text** and synthesize each piece to a **complete WAV**; do **not** slice one WAV into raw byte fragments.
- **`seq` must be ascending/contiguous/non-duplicate** starting at 0 (the app sorts audio parts by `seq`).

### Option B — Swap the TTS model
Use a TTS model without the ~60 s ceiling (or a higher one). Removes the need to chunk, at the cost of VRAM/latency/model-availability on the inference host. Pure infra decision.

### Option C — Cap voice-mode reply length
Constrain the tutor's reply to ~150 words when the turn is a voice turn, so a single synthesis fits under the cap. A product/UX choice (shorter spoken answers) rather than an engineering fix; also reduces per-turn latency.

---

## App-side readiness (no change required)

Confirmed by a read of the client: a backend that emits `[{seq,chunk_id,url}, …]` with ascending `seq` **Just Works** — the single-chunk case today is the N=1 case of the same path.
- Parse: `http_voice_api.dart:125-136` (whole `audio[]` → ordered `AudioAnswerPart`s).
- Select + order + fetch + play: `session_screen.dart:468-480`; playback `audio_playback.dart:37-53`.
- Model already supports N ordered parts: `AudioAnswerPart{seq, chunkId}` (`voice_api.dart:71-86`).

**Two client characteristics worth knowing (not blockers, pre-existing):**
1. **Serial fetch, 10 s per chunk** — `fetchAudioChunk` has a 10 s timeout each (`http_voice_api.dart:358`) and the fetch loop is serial, so N chunks ⇒ up to N×10 s of fetch budget. Keep chunk count modest and each chunk small.
2. **Playback starts only after all chunks are fetched** — `_playAnswer` fetches the whole list *before* `playSequential` (`session_screen.dart:472-480`), so pre-audio latency = sum of chunk fetch times. Same behavior as today for N=1; just scales with N. (A future app-side improvement could stream/play chunk 0 while fetching the rest — flag it if the count grows, but it's out of scope for this fix.)

## Contract note (no re-pin needed)

The voice Rev 1 response shape is `{ transcript, tutor_response, audio: [{seq, chunk_id, url}] }` and `audio` was **always an array**. Emitting more than one element is the N>1 case of the existing shape — **additive-safe, and it does not disturb the frozen voice `CONTRACT_SHA`/`BINDING_SHA`** (binding `docs/design/contracts/API-session-http-binding.md`). No field renames, no new fields, no status-code changes.

---

## Resolution (spark session, 2026-07-26 — Option A, three iterations)

Implemented in `src/study_tutor/voice/service.py` (`split_text_for_tts` +
capped serial synthesis loop + deferred chunk storage) with tests in
`tests/unit/voice/test_service.py` (148 green across the voice surface). Every
iteration was gated by an independent workflow coach; the two intermediate
FAILs below are why the final shape is what it is.

**Refined root-cause model:** the ceiling is **~170–180 *words*, not 60 s of
wall-clock** — 120-word pieces render fully at 45–68 s of audio; a 360-word
single call truncated to 42 s. Splitting at 120 words leaves real headroom.

- **v1 — serial chunking, store-as-you-go.** Correct (574-word reply → 6
  chunks, 259.8 s of audio at 2.21 words/s, seqs 0..5, every chunk an
  independent RIFF WAV) but the E2E gate FAILED it: 6 serial syntheses ≈
  105 s → 127 s wall vs the 90 s deadline, and chunk 0 had burned ~80% of its
  120 s ChunkStore TTL before the response even returned.
- **v2 — bounded-concurrency (2) + TTL-deferred storage.** The adversarial
  review REFUTED concurrency with live measurements: **the TTS server
  serializes generation behind its model lock**, so a queued request streams
  no bytes until the active one finishes — the client's 10 s httpx **read**
  timeout (which serial calls dodge because the WAV streams progressively)
  then kills it, the freed semaphore admits the next piece against a
  still-busy backend, abandoned streams hold llama-swap slots (429s), and
  failures cascade: 4-piece reply → 1 chunk; deployed E2E: 526-word reply →
  1 of 5 chunks (52 s of audio). Strictly worse than the original bug.
- **v3 (FINAL) — serial + `TTS_MAX_PIECES_PER_TURN = 2` + TTL-deferred
  storage.** Serial is the reliable path (streaming keeps the read timeout
  fed; v1 proved 6/6 pieces). The piece cap bounds wall time deterministically
  (~2 × 17–30 s TTS + LLM ≈ 60–75 s worst): replies ≤ ~240 words get **full
  audio** (this covers the 182- and 242-word cases that motivated this
  investigation); longer replies speak their first ~240 words (≈ 99 s of
  audio — still ~1.7× the old cap) with the tail on screen as text, logged
  (`"Voice reply of N pieces capped to 2"`). Chunks store only after all
  synthesis, so the 120 s TTL starts at response time.

**Final E2E evidence (PASS, 12:33–12:44 UTC, as alex):** 160-word reply →
2 chunks (46.5 + 20.5 s), 38.4 s wall · 224-word reply → 2 full chunks
(49.8 + 49.1 s), 50.3 s wall · **509-word reply → capped 2 chunks, 99.0 s of
audio, 59.8 s wall** with the cap log line present. Zero TTS failures, zero
429s, zero tracebacks; chunk 0 re-fetched at +61 s → 200 (and a +140 s fetch
correctly 404'd — TTL expiry works); co-tenants and kernel log clean; contract
shape unchanged.

**ASSUM-005 partial-failure policy (documented choice):** the contiguous
prefix of successfully synthesized pieces is returned — partial audio, never
a gap; a first-piece failure yields `audio=[]` exactly as before.

**Recommended follow-ups (not blocking):**
1. **Option C remains the product-level companion**: capping voice-mode
   replies at ~240 words would make the piece cap moot and cut latency.
   Until then, >240-word replies are deliberately part-spoken.
2. `audio_timeout_seconds` (10 s) survives long syntheses only because the
   server streams; a >10 s stall mid-stream would still kill a piece
   (pre-existing exposure, unchanged by this fix).
3. Disclosure: during v2 verification the review agent's live TTS probes
   followed the code-default URL and exercised the **GB10's** qwen3-tts
   container (same image/config as spark's — conclusions transfer), leaving
   it needing a ~2 min drain. Transient, no lasting effect; the GB10 audio
   pair is slated for decommission post-soak anyway.

## Related (already landed on `main`, for context)

Getting to this point fixed three prior app-side voice bugs, all merged: the recorder permission/temp-path/empty-file crashes (`8203d86`), the voice-turn deadline 30→90 s (`56b832e`), and — the one that was masking this — the response-shape parser (`92fd107`, the app was reading a nonexistent `answer_parts` instead of `tutor_response` + `audio[]`). With those in, the round-trip works end-to-end; this ~60 s audio cap is the remaining polish item and it's a backend/inference concern.
