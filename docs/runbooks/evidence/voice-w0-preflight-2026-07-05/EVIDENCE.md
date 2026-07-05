# W0-T — tutor voice pre-flight evidence (2026-07-05)

**Gate:** [voice scope & build plan §5 W0-T](../../../research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md) (blueprint §8 Phase 0).
**Run from:** Linux dev box → `http://promaxgb10-41b1:9000` (llama-swap front door).
**Result: ALL FOUR GATES PASS.**

## 1. `GET /v1/models` lists both audio models — PASS

`parakeet-tdt-0.6b-v3` and `qwen3-tts-0.6b` both present in the model list.

## 2. `GET /running` shows both `ready` — PASS

Running set at test time: `coach-ft-v3`, `embed`, `nomic-embed`,
**`parakeet-tdt-0.6b-v3` (ready)**, `qwen-graphiti`, **`qwen3-tts-0.6b` (ready)**,
`qwen36-workhorse`. Note: `gemma4-tutor` was **not** resident (on-demand,
`ttl: 1800`, `tutor` set only) — the R-G5 resident-set question observed live.

## 3. TTS `voice=Ryan` returns playable audio — PASS

`POST /v1/audio/speech` `{model: qwen3-tts, voice: Ryan, input: <13-word sentence>, response_format: wav}`

| Metric | Value |
|---|---|
| Latency (whole-file wav, 13 words) | **2.09 s** |
| Size / header | 211,244 bytes, valid `RIFF…WAVE` |
| Intelligibility (objective, no listener) | round-tripped through live STT → transcript matches (see 4) |

Consistent with the blueprint's ~1–2 s/sentence whole-file figure.

## 4. STT round-trips known-text clips, including m4a — PASS

Input sentence: *"The quick brown fox jumps over the lazy dog near the river bank."*
All three formats transcribed as *"The quick brown fox jumps over the lazy dog
near the riverbank."* — compound-word join only; semantically exact, punctuation
and capitals present.

| Format sent to `/v1/audio/transcriptions` | Content-Type | Latency (warm) |
|---|---|---|
| wav (TTS output) | `audio/wav` | **0.29 s** |
| ogg/opus (GStreamer `opusenc`→`oggmux`, 32 kbps) | `audio/ogg;codecs=opus` | **0.11 s** |
| **m4a (AAC-LC 44.1 kHz mono 128 kbps, ffmpeg)** | `audio/mp4` | **0.15 s** |

All inside ADR-ARCH-024 r1's warm 0.09–0.35 s band.

## Caveats / follow-ups

- The m4a was ffmpeg-encoded AAC-LC — a close proxy for the Flutter `record`
  package's default output, **not a real device recording**. Re-verify with a
  real phone-recorded m4a before freezing the recorder config (already a W2a
  note in the design §6.1).
- `GET :9000/speakers` returns 404 through the llama-swap front door (it
  proxies `/v1/audio/*` only). Not a gate failure — `voice=Ryan` proven by the
  speech call itself. If the speakers list is ever needed, use the container's
  route directly (or llama-swap's per-model upstream path).
- W0-R (Reachy feasibility gates R-G1..R-G5) **not run from this box** — no
  passwordless SSH to the GB10; needs operator access (tracked in plan §0).

## Repro commands

```bash
curl -sS http://promaxgb10-41b1:9000/v1/models
curl -sS http://promaxgb10-41b1:9000/running
curl -sS -o out.wav -H "Content-Type: application/json" \
  -d '{"model":"qwen3-tts","voice":"Ryan","input":"<sentence>","response_format":"wav"}' \
  http://promaxgb10-41b1:9000/v1/audio/speech
curl -sS -F "file=@out.wav;type=audio/wav" -F "model=parakeet-tdt" \
  http://promaxgb10-41b1:9000/v1/audio/transcriptions
# ogg/opus: gst-launch-1.0 filesrc ! wavparse ! audioconvert ! audioresample ! opusenc bitrate=32000 ! oggmux ! filesink
# m4a:      ffmpeg -i out.wav -c:a aac -b:a 128k -ar 44100 -ac 1 out.m4a
```
