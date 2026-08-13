# RESULTS — the Flutter-web boot claim (Mac leg, 2026-08-13)

**Leg:** [`HANDOFF-mac-web-boot-leg-2026-08-07.md`](HANDOFF-mac-web-boot-leg-2026-08-07.md) —
establish an honest Flutter-web boot claim so Lane 3 step 4 (upload-surface vehicle) stops
being decided blind. Run on the Mac, `app/` only; **no server file, no contract, no client
code was touched** (this leg is diagnosis, not build).

**Verdict in one line: it BOOTS and the full text walk passes against the live spark — but
only with browser security disabled, because `:8100` serves no CORS headers. In a real
browser today, every API call is blocked.**

Environment: Flutter 3.44.4 / Dart 3.12.2; Chromium 141.0.7390.37 (Playwright, headless);
served from `python3 -m http.server` on `127.0.0.1:5011`; target
`http://spark-fcf6.tailebf801.ts.net:8100` (live spark, `{"status":"ok"}` on `/healthz`).
Gates re-run after the leg: `flutter analyze` **clean**, `flutter test` **424/424 green**
(the 2026-08-04 baseline, unmoved — no code changed).

---

## 1. Does it compile? — YES

`flutter build web` succeeds unmodified (`✓ Built build/web`, ~18s). No conditional-import
work, no plugin surgery, no `dart:io` build break. Two caveats worth recording:

- **No wasm build.** The dry run reports `flutter_secure_storage_web` using `dart:html`,
  `dart:js_util` and `package:js`. The JS build is unaffected; `--wasm` is simply not
  available while that dependency stands.
- **`dart:io` compiles, it does not protect you.** `lib/adapters/audio_playback.dart:10`,
  `lib/adapters/voice_recorder.dart:12` and `lib/adapters/http_voice_api.dart:12` all import
  `dart:io`, and `voice_recorder` calls `getTemporaryDirectory()` while `audio_playback`
  touches `Directory.systemTemp` / `File`. I verified separately (`dart compile js` on a
  one-line `dart:io` program — compiles fine) that dart2js supplies a **stub**: these are
  **runtime** failures on web, not build failures. "It compiles" is therefore not evidence
  that the voice/audio path is web-safe; those paths are simply never reached in this walk.

## 2. Does it boot? — YES

Real sign-in screen paints via CanvasKit: "Study Tutor", the tagline, the Sign-in button and
the table-auth chips (Lilymay / Alex). `FLUTTER-VIEW` host present, **zero page errors**,
zero console errors other than the CORS ones below. First load transfers **~4.96 MB
uncompressed** (`main.dart.js` 2.90 MB + `canvaskit.wasm` 1.57 MB) off a static server with
no gzip/brotli — a compressing server would cut this substantially, but the order of
magnitude is a multi-megabyte boot for the whole app.

## 3. The hard wall: no CORS on `:8100`

**This is the finding.** There is no CORS middleware anywhere in `src/` (grep: zero hits),
and the deployed server confirms it:

| probe | result |
|---|---|
| `OPTIONS /api/sessions/start` (with `Origin` + `Access-Control-Request-*`) | **405 Method Not Allowed** (`allow: POST`) |
| `GET /healthz` with `Origin:` | 200, **no `access-control-allow-origin` header** |

So the browser blocks every call the app makes. Verbatim, from the sign-in step:

```
Access to fetch at 'http://spark-fcf6…:8100/api/student-model?subject=english'
from origin 'http://127.0.0.1:5011' has been blocked by CORS policy:
Response to preflight request doesn't pass access control check:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```
```
GET …/api/student-model?subject=english  :: net::ERR_FAILED
GET …/api/sessions?status=active         :: net::ERR_FAILED
```

Note *why* preflight is unavoidable: the app sends `authorization: Bearer …` (and
`content-type: application/json` on writes), which makes every request non-simple. There is
no header-trimming trick that dodges this — the server must answer `OPTIONS` and emit
`Access-Control-Allow-Origin`/`-Headers`. **This is a server-side change and was left
undone by fence.**

**The app degrades gracefully, which is the good news:** a "Connection problem — Couldn't
reach the tutor. Check your connection and try again." dialog, no crash, no white screen.
One cosmetic nit: behind the dialog the home screen renders its "No sessions yet — start one
below" empty state, so once the dialog is dismissed a *network failure* is indistinguishable
from *a genuinely empty history*.

## 4. Isolating the blocker: with CORS disabled, everything works

Re-run with `--disable-web-security` (a **diagnostic**, not a claim of working software) to
separate "the web client is broken" from "the server lacks a header". Walked as **Alex**
(the handoff's rule: Lilymay read-only — the Lilymay pass was sign-in only, no session
started). Every call 200, no page errors:

| step | call | result |
|---|---|---|
| sign in | `GET /api/sessions?status=active` | **200** |
| sign in | `GET /api/student-model?subject=english` | **200** — gamification card renders live ("Level 1 · Beginner", 0 XP, no streak) |
| start | `POST /api/sessions/start` | **200** |
| home | *(no call)* | active-session **disclosure card** renders — "Continue: Metaphor Identification · 0 turns · 2m ago" + Resume. The never-a-silent-resume UI works on web. |
| resume | `GET /api/sessions/{id}/resume` | **200** |
| **turn** | `POST /api/sessions/{id}/turn` | **200** — a real, correctly Socratic tutor reply rendered ("Think about the phrase perhaps *The classroom was a zoo*… What do you think I'm trying to suggest?") |
| end | `POST /api/sessions/{id}/end` | **200** — "Session complete · +0 XP · 0-day streak" settlement sheet renders |

**Conclusion: CORS is the only thing standing between Flutter web and a working text
tutoring session.** The client code needs no changes to boot, authenticate (table flavour),
converse, or settle.

Screenshots: `evidence/` was not disturbed; captures live in the session scratchpad
(boot, CORS dialog, gamification card, live tutor turn, mic banner, settlement sheet).

## 5. Voice on web — broken, gracefully, as expected

Tapping the mic yields the banner **"This app needs microphone access to record your
questions"** — *both* with permission denied *and* with microphone permission pre-granted
plus a fake media device. The gate is `record`'s `hasPermission()`
([`voice_recorder.dart:76`](../../app/lib/adapters/voice_recorder.dart#L76) →
[`:150`](../../app/lib/adapters/voice_recorder.dart#L150) `MicrophonePermissionDenied` →
[`session_screen.dart:327`](../../app/lib/ui/session_screen.dart#L327)). Per the handoff I
did **not** chase it. Stated honestly: web voice is blocked at the mic gate in headless
Chromium; an attended check in a real browser is needed to tell "`record_web` genuinely
can't get permission here" from "headless artifact". Either way §1's `dart:io` /
`path_provider` stubs sit directly behind that gate, so web voice is more than a
one-line fix.

## 6. Incidental server-side observations (NOT actioned — outside this leg's fence)

- `GET /api/sessions?limit=abc` → **500** (`{"error":"Internal server error"}`). A
  non-integer query param should be a 422. **Unreachable from the app** (the adapter always
  formats an int), so this is robustness, not a live bug.
- One **transient 500** on the very first `/api/sessions?limit=3` request of the session,
  not reproducible on any subsequent probe. Recorded for the record; possibly a cold-start
  artifact. Not investigated.

## 7. Recommendation for Lane 3 step 4 — **build the upload surface as a minimal separate
page, served same-origin by the tutor server**

The boot claim is now positive, so this is a *choice*, not a forced move — but the evidence
points away from Flutter web **for this particular surface**, for four reasons:

1. **Same-origin deletes the CORS problem instead of solving it.** A page served by the
   tutor server itself has no cross-origin call to authorise. Choosing Flutter web means
   either adding and maintaining a CORS allowlist on `:8100` (a new security surface that
   grows with every origin/domain in the TLS work) or serving the Flutter bundle
   same-origin anyway — at which point the multi-megabyte bundle is pure cost.
2. **`flutter_appauth` has no web support — verified**, not assumed: its pubspec registers
   `android`, `ios`, `macos` only. The walk above passed on the **table-auth dev flavour**;
   the pilot's real Keycloak flavour would need a *second, different* OIDC implementation
   written for web. That is the single largest hidden cost in the Flutter-web option, and it
   lands squarely on the auth path.
3. **Weakest-case fit.** An upload surface is a file picker, a progress bar and a result
   list — precisely what plain HTML does in kilobytes and canvas-rendered Flutter does
   awkwardly (drag-and-drop, accessibility, form semantics). ~5 MB of CanvasKit to render a
   file input is the wrong trade.
4. **It decouples release cycles.** Scanned-guide upload is an occasional, likely desktop
   task; the tutor app is a daily mobile one. Keeping them apart means the upload surface
   can ship, be quota-guarded and be hardened next to the ingest endpoint without touching
   the app's release train.

**What the positive boot claim does buy us:** if a browser-based *tutoring* client is ever
wanted (a school desktop, a Chromebook, a "try it without installing" link), Flutter web is
a live option and the client needs no rework to reach it — the cost is a CORS allowance,
a web OIDC adapter, and accepting no voice and no wasm. That is a real option we did not
have yesterday, and it should be recorded as such rather than spent on the upload page.

---

**Fence compliance:** `app/` only; no server file, contract, or client code modified; no
NATS broker contacted (HTTP `:8100` only, as the handoff directs). Live writes were confined
to student **Alex** per the handoff; the two sessions the walk created were **ended**
afterwards (`POST /end` → 200, `?status=active` → `[]` confirmed) so no dangling active
session was left on the spark.
