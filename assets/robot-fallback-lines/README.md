# Robot fallback lines — rendered in the tutor's voice

Three WAVs for the Reachy Scholar app to play when a turn fails. Ruling E1c
leaves the robot with no local TTS, so a failed turn was otherwise **silent**
— a child could not tell "I didn't hear you" from "I'm broken". Requested by
the fleet-gateway session (2026-08-14 handoff, item 3), which had been
shipping macOS `say` renders.

| File | Line |
|---|---|
| `misheard.wav` | "I didn't quite catch that. Could you say it again?" |
| `tutor-unreachable.wav` | "I can't reach the tutor just now. Let's try again in a moment." |
| `not-configured.wav` | "I'm not set up yet. Could you ask a grown-up to check my settings?" |

**Format:** WAV, 24 kHz, mono, 16-bit PCM — 3.8 s / 6.3 s / 6.5 s.

**Voice:** `qwen3-tts-0.6b`, voice `Ryan`, via the spark's llama-swap
(`:9000/v1/audio/speech`) — the exact model and voice the live voice turns
use (`TTS_MODEL` from `deploy/http/.env`; `TTS_VOICE` is empty, so
`VoiceConfig`'s default `Ryan` applies). So these are the tutor's voice, not
a lookalike.

Worth deciding rather than inheriting: the handoff argued a *distinct*
voice is arguably more honest here, since it is the robot speaking for
itself rather than the tutor. These are rendered as asked (the tutor's
voice); re-render with another `voice` from `GET :5807/v1/models` if you
would rather they sounded like the robot.

**Re-rendering:** the sizes are patched after synthesis — llama-swap streams
WAV with placeholder `0xFFFFFFFF` RIFF/data lengths, which is fine for a
stream and wrong for a file that ships in an app package. Any re-render must
patch them too, or players will guess at the duration.
