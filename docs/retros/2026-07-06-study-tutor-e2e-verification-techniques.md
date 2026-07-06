# Retro: How study-tutor was verified end-to-end — techniques for the guardkit QA Verifier

**Date:** 2026-07-06. **Author:** Claude (Mac session) with Rich.
**Subject:** the verification methodology that took the Flutter app from fake-backend v1 through phase-2 real transport to a live cross-device proof (waves p2-1…7, 2026-07-04/05) — extracted as reusable techniques for guardkit's QA Verifier.
**Evidence base:** `app/PROGRESS.md` (per-wave ledger), `app/QUESTIONS.md` (triage record), `docs/runbooks/RESULTS-study-tutor-p2-live-acceptance-2026-07-05.md` (acceptance record incl. the five-attempt live-suite ledger), git history `4be98b2..aa94365`.

**Headline numbers:** 125 hermetic tests, 35 of them run unmodified against both a fake and the real backend; 5 wave-level adversarial reviews (43 raw findings → 19 confirmed → every confirmed finding fixed pre-commit); 3 real backend bugs found by the live suite on first contact; 1 cross-device walk, 10/10 checkpoints observed clean on the emulator. Zero bugs found *after* acceptance so far.

---

## 1. The verification stack (outermost first)

Each layer catches a class of defect the layers below cannot. The QA Verifier should think in these layers, not in "run the tests".

### L1 — Pre-registered pass criteria
The success bar was written into the build plan **before building**: "live contract suite green against the real adapter and the fake (same assertions) + §3.6 walk clean + hermetic suite green with pre-phase tests unmodified in substance." Every later dispute ("is this done?") reduced to checking a document that predated the work. The walk itself was a **scripted checkpoint list** (start + 2 turns → curl same-student list/turn/resume → re-resume shows all six messages in order → end → status ended/resumable:false), each step pass/fail observable.

**Extract:** the Verifier's first artifact is the pass bar, pinned before implementation; acceptance is evaluated against that text, never against the implementer's memory of intent.

### L2 — Frozen contracts with pinned SHAs, and an arbiter rule
The transport-neutral contract (CONTRACT_SHA) and the HTTP binding table (BINDING_SHA) were frozen commits. The standing rule: **any live disagreement is triaged app-bug vs backend-bug vs contract-gap, with the pinned doc as arbiter — never adapt the consumer silently.** This is what let the live suite *find* backend bugs (`timestamp` vs the binding's `ts`; row-counted vs pair-counted `turn_count`) instead of the app quietly absorbing them.

**Extract:** the Verifier needs a named arbiter document for every seam it tests, and a triage rubric that assigns each failure to a side. A failure without attribution is an unfinished verification.

### L3 — One suite, two backends (the contract-suite moat)
The 35 contract tests were written against the port (`SessionApi`) and parameterized by a backend factory (`ContractBackend`): the hermetic gate runs them against an in-memory fake; `test_live/` imports **the same test bodies** and runs them against the deployed server. "Fake and backend agree" became a test run, not an argument. The abstraction deliberately exposes *expectation seams* where the two backends legitimately differ (`expectedTutorReply`: exact canned string on the fake, non-empty on a live LLM; `advancedFrom`: strict tick-clock vs at-or-after) — so loosening is explicit and reviewable, never smuggled into test bodies.

**Extract:** when a fake/mock exists, the Verifier should demand the *same assertions* run against the real thing, with any fake-vs-real expectation differences expressed as named seams in a harness, not as forked test files.

### L4 — The hermetic gate, mechanically enforced
Per wave: `flutter analyze` clean + `flutter test` green + `flutter build apk --debug`, one commit per wave, tick + log inside the commit. Hermeticity was made *structural*, not conventional: the live suite lives outside the default test tree (`test_live/`), and a **composition assertion test** pins that the gate's build wires the fake (`apiBaseUrl` empty ⇒ `FakeSessionApi`) — the gate cannot accidentally reach a server because a test fails if it could.

**Extract:** the Verifier should check that hermetic/live separation is enforced by structure (location, compile-time define, an assertion test) rather than by convention or tags.

### L5 — Adversarial review with execution probes, per change
Every wave's diff got a multi-lens review (correctness / plan-compliance / consistency, lenses varied by wave) whose findings were then **independently refuted-or-confirmed, with execution as the standard of proof**. The verifiers ran probes: throwaway scripts against the real adapter code with MockClient, mutation probes on tests, even engine-binary inspection. This is the layer that caught what green tests cannot:

- **Mutation-verification of tests:** deleting the auth header from `resumeSession` left all 13 unit tests green → the missing per-verb header pins were a *proven* coverage hole, not an opinion.
- **Non-conforming-input escapes:** a proxy-style nested `error` object threw a raw `TypeError` past the sealed exception hierarchy; out-of-enum wire values threw raw `ArgumentError` — both probe-verified crashes that a conforming-fixtures-only suite could never see.
- **Claimed-behavior vs actual-platform:** the Android `network-security-config` was verified **down to the engine binary** to not govern `dart:io` traffic at all — the docs were rewritten to say what the config actually does, and the false security claim never shipped.

**Extract:** the Verifier should (a) mutate the code under test and require the new tests to go red, (b) feed *non-conforming* inputs at every boundary (the closed-set escape hatch must catch garbage, not just documented errors), and (c) treat "the platform docs say so" as a claim to probe, not a fact.

### L6 — Live acceptance as an instrumented campaign, not a single run
Five live-suite attempts, each recorded in an attempts ledger with deployment state, harness settings, result, and attribution. Key behaviors that made the campaign converge:

- **Probe before rerunning.** After failures, single curl probes characterized the system (one turn: how long? what shape came back?) before burning a 20-minute suite run. The `timestamp`/`ts` and `turn_count` bugs were pinned by *one* probe each.
- **Warm-up before timed runs.** Model cold-loads (~22–66s) were absorbed by a throwaway turn before any latency-sensitive run, so the first test never measured the cold path.
- **Measure at the right cadence.** The backend's "8.5s warm" claim was validated only for first turns; probing turns 1→4 in one session exposed 36–48s with history. Later, the suite's zero-think-time cadence itself became a confound. Rule: validate latency claims at the *consumer's* cadence, and know which cadence your test harness produces.
- **Hunt confounds before concluding.** The attempts 3–4 degradation was first attributed to a Coach-queue design flaw; Rich's concurrent LPA workload on the same GPU was the real cause (llama-swap eviction). The disambiguating rerun on a quiet GPU (35/35 in 3m33s) exonerated the design. The correction was committed to the record the same day.
- **Harness deadlines are declared accommodations.** When the harness tolerated out-of-budget latency (120s/90s/60s vs the contract's 30s ceiling), the deviation was loudly documented in code comments + QUESTIONS.md as a backend conformance gap — the harness never silently normalized a violation, and the *product* deadline (15s) was never touched.

**Extract:** the Verifier keeps an attempts ledger; probes before re-running expensive suites; warms caches/models before timing; validates performance claims at consumer cadence; treats environmental confounds (shared GPU/CI noise) as hypotheses to disambiguate with a controlled rerun; and records any harness leniency as a named, temporary accommodation.

---

## 2. The emulator walk: driving the real app to prove the slice (the technique Rich asked for)

The final proof was not a test at all — it was the **real APK, on the real Android emulator, against the real deployed backend over the real network**, driven step-by-step with a human watching. Mechanics, exactly as executed:

1. **Build the real flavour:** `flutter build apk --debug --dart-define=API_BASE_URL=http://<tailscale-ip>:8100` (compile-time composition — the artifact under test IS the artifact that ships the behavior). `adb install -r`, `adb shell am start -n <package>/.MainActivity`.
2. **Pre-condition the environment:** health-check the backend from the driving machine first (`curl /healthz`); warm the model with a throwaway turn; reset server state via the dev route so the walk starts from a documented blank slate.
3. **Screenshot → verify → act loop.** Every step: `adb exec-out screencap -p > step.png`, read the image, *verify the expected state visually* (right screen, right text, no error dialog), then act — `adb shell input tap X Y` (scale coordinates if the screenshot is downsampled: displayed × factor = device pixels), `adb shell input text 'foo%sbar'` (`%s` = space), waits sized to the operation (LLM turns got ~20s before the verification screenshot).
4. **Interleave the second device.** Cross-device claims were proven by alternating surfaces mid-walk: emulator does turns → curl (as the same authenticated user) lists/advances/resumes and asserts JSON (`turn_count: 2`, six ordered turns) → emulator re-resumes and the *screenshot* shows all six messages including the curl-injected pair. The UI and the API were witnesses to each other.
5. **Checkpoints are pre-registered and each produces evidence.** Ten checkpoints, each with a named artifact (screenshot or curl JSON), recorded in a RESULTS doc alongside the suite-attempts ledger. "Pass = every step observed" — an unobserved step is a failed step.
6. **Negative-space checks ride along.** Not just "the message appears": the ended state asserts the input is disabled, the End affordance is *gone*, the ended session *dropped off* the home list — absence assertions, which screenshots prove well.

Why this layer exists at all: it catches the wiring class of bug that every stub-injected suite misses. The sibling evidence from the same fortnight: the GB10's `serve-http` had a reply closure calling a **nonexistent** `orchestrator.orchestrate` — every real turn 500'd, invisible to every unit/integration test because they all injected stubs; it surfaced only when the runbook drove the wired path. Same lesson as lpa-platform-poc's "green but broken" voice AutoBuild (14 post-merge defects, mocked seams). The walk is the anti-stub-blindness instrument.

---

## 3. What each layer actually caught (evidence)

| Layer | Real defects caught here |
|---|---|
| Hermetic gate (L4) | Ordinary red-green development churn; analyzer drift (lint regressions on every wave, fixed same-commit) |
| Adversarial review (L5) | Raw `TypeError`/`ArgumentError` escapes past the sealed error set; missing auth-header pins (mutation-proved); no retry affordance on home refresh; NSC-doesn't-govern-dart:io false docs; live-harness 15s deadline that would have mis-triaged contract-legal 30s turns |
| Live suite, same assertions (L3+L6) | `timestamp` vs `ts` wire field (8 tests); row-counted `turn_count` (4 tests); Coach latency chain (sync Coach → wrong model → 43s warm turns) |
| Probes (L6) | Exact wire shapes for both bugs in one request each; the LPA-workload confound; turn-depth latency scaling the backend's own validation missed |
| Emulator walk (L2 of proof) | Confirmed no wiring-class bug existed in the app (its sibling technique caught `orchestrator.orchestrate` on the backend); proved the cross-device semantics a suite can only simulate |

## 4. Recommendations for the guardkit QA Verifier

1. **Demand the pass bar before the build** (L1). Refuse to verify against unstated criteria; write the checkpoint list into the task/feature doc and evaluate only against it.
2. **Name the arbiter per seam** (L2). Every cross-component failure gets attributed (this-side / other-side / contract-gap) before the verification is "done".
3. **Same assertions, real backend** (L3). Where a fake exists, require the factory-parameterized harness pattern; reject forked live tests. Expectation differences must be named seams.
4. **Check hermeticity structurally** (L4). Location/compile-time separation plus a composition assertion — not tags, not convention.
5. **Mutation-check new tests** (L5). At minimum: revert or break the key behavior and require reds. A test that survives its own mutation is a finding.
6. **Probe non-conforming inputs at boundaries** (L5). Garbage envelopes, out-of-enum values, wrong types — the error posture must degrade, never leak raw errors.
7. **Run the wired path** (§2). If the deliverable has a runtime surface, drive it for real: emulator/browser via screenshot-verify-act, real backend if one is deployed, evidence artifact per checkpoint, negative-space assertions included. Stub-injected green is not evidence of a working system.
8. **Instrument acceptance campaigns** (L6): attempts ledger, probe-before-rerun, warm-up before timing, consumer-cadence latency validation, confound disambiguation via controlled rerun, and loudly-documented (never silent) harness accommodations.
9. **Correct the record when attribution changes.** The confound correction (Coach exonerated) was a same-day commit. A verifier that never revises its verdicts trains people to ignore them.

---

*Companion retros: `2026-07-03-autobuild-self-defeating-boundary-tests.md` (why mocked seams lie), and the call-site-drift retro that produced the READY-boot-smoke rule this phase inherited.*
