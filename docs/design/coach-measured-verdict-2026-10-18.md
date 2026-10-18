# Design — the Coach's verdict is computed, and it catches the weak replies it waves through today

2026-10-18 · Rich's instruction (18 Oct): work the remaining items from ai-transition
`docs/handoffs/study-tutor-models-brief-2026-10-18.md` with `cross-model-build`. Brief item 5: "The coach accepts subtly
weak replies (4 of 5 weak replies from the May base-vs-fine-tune evaluation), and the app trusts the model's own total
score (`parse_coach_output`) instead of computing it."

## What is true today (receipts)

* **The model's total and decision are trusted.** `parse_coach_output` (`tutoring/coach/rubric.py:642-704`) validates
  the JSON and drops unknown criterion ids, but never recomputes `weighted_total` or `decision`; the weights
  (`DEFAULT_WEIGHTS`, `rubric.py:200-207`: accuracy .20, AO .20, scaffolding .15, language .10, feedback .15, quote .20)
  and `ACCEPTANCE_THRESHOLD = 0.70` (`:85`) are used only by `score_rubric`, which has no production caller. The prompt
  (`roles/tutor/prompts/coach.md`) never states weights or threshold, and its only example is `0.82 / accept`.
* **Production runs the Coach after delivery.** `cli/main.py:395-409` builds the orchestrator with
  `coach_evaluation="async"`; a non-accept only logs `async_coach_below_threshold` (`orchestrator.py:1103-1145`). So this
  change alters review flags and the revise path's guidance, not what a learner sees today.
* **Measured 18 Oct, live Coach (deployed prompt, `tutor-coach` = the factory's Qwen3.8 model), the May eval's replies**
  (`tests/fixtures/coach/may-eval-baseline-verdicts-2026-10-18.json`; replies and human labels from
  `docs/runbooks/evidence/base-vs-finetune-eval/`). Weak = the five fine-tune replies meeting ≤ 1/3 of the expected
  behaviours; clean = the nine replies meeting all of them with no red flag:

  | | accepted by the Coach | lowest criterion score given |
  |---|---|---|
  | 5 weak | **5 / 5** (model totals 0.78–0.95) | 0.6 |
  | 9 clean | 9 / 9 | 0.9 |

  `misconception-01` (the tutor *agreed* with the learner's wrong date — the eval's red flag) got
  `curriculum_accuracy = 1.0`. The model's own totals disagree with the weighted sum by up to 0.10.

So the arithmetic fix alone changes nothing on this evidence (the computed totals are all ≥ 0.88, and no weak reply
scores below 0.6 on any criterion): the Coach model is **scoring the failures high**. Both halves are needed.

## The fix

### C1 — compute the verdict (honest totals and decisions)

In `rubric.py`, `parse_coach_output`'s dict and JSON-string branches (after `_drop_unknown_criteria`) recompute:
`weighted_total` = the weighted sum of the six canonical criteria with `DEFAULT_WEIGHTS` (one shared helper with
`score_rubric`, so the two cannot drift); `decision = "accept"` only when the total ≥ `ACCEPTANCE_THRESHOLD` **and** no
floor below is breached, else `"revise"`. A rubric missing any of the six criteria raises `MalformedCoachOutputError`
("incomplete rubric: missing [...]") — the existing unevaluated-turn fallback — rather than inventing scores; a duplicated
criterion keeps its lowest score. When the computed decision is revise and the model gave no `rubric_feedback`, it is
filled from the existing `_build_feedback`. A disagreement with the model's own total (> 0.05) or decision is logged as
`event=coach_total_disagreement` with the values in the message text. The already-built `CoachVerdict` branch (tests'
hand-built verdicts) is unchanged.

**Floors (law-level only):** `curriculum_accuracy < 0.5` or `quote_fidelity < 0.5` forces revise whatever the total —
a factual error or a misquotation is never outweighed by friendliness. Applied in `score_rubric` too.

### C2 — anchor the Coach prompt on the failure patterns it misses, and measure

`coach.md` gains short scoring anchors drawn from the five missed replies (no new criteria, no weights in the prompt):

* agreeing with, or not correcting, a factual error in the learner's message ⇒ `curriculum_accuracy` ≤ 0.2;
* replying only with questions when the learner asked for an explanation, method or exam technique ⇒
  `constructive_feedback` and `ao_alignment` ≤ 0.4;
* helping with an off-subject request instead of briefly declining and redirecting ⇒ `ao_alignment` = 0;
* a reply that is friendly and Socratic but gives no usable next step is not a 1.0 on `constructive_feedback`;

and the example's `weighted_total` / `decision` are labelled as computed by the app (the model may still emit them; C1
ignores them for the decision).

**Acceptance is measured, and its claims are limited to what the data can show** (Codex design review round 1, R1/R2).
The eval has 32 labelled replies (`criteria_judgements.jsonl`, keyed by `(id, side)`): **5 weak** (fine-tune, ≤ 1/3 of
expected behaviours: misconception-01, exam-technique-01, exam-technique-02, scaffolding-02, boundary-01), **11 clean**
(all behaviours, no red flag: nine base replies — the selected tuning controls — plus fine-tune essay-feedback-01 and
quote-analysis-01), and 16 in between (8 at 5/6, 7 at 2/3, 1 at 1/2). All five weak replies were used to write the
anchors, and the repo holds no other independently labelled weak replies (the multi-turn eval is judged per session,
not per turn). So:

* **Detection is claimed only on the five seen weak replies**, not on unseen ones. Bar: more weak replies revised than the
  baseline's 0 / 5.
* **No-harm is claimed on all 27 others**, 18 of which were never looked at while writing the anchors. Bar: **0 of the 11
  clean** revised, and **at most 2 of the 8** replies at 5/6 revised.
* **Generalisation to unseen weak replies is explicitly not established.** Named follow-up: an independently labelled set
  of weak and good single-turn replies (labelled blind, before scoring) to measure detection; the prompt is frozen until
  then.

**Measured 18 Oct (candidate prompt 1, frozen; one sample per reply; verdicts committed as
`tests/fixtures/coach/may-eval-candidate1-verdicts-2026-10-18.json`), with the C1 decision rule:** weak **2 / 5** revised
(misconception-01: `curriculum_accuracy` 0.1, was 1.0; boundary-01: `ao_alignment` 0.0); clean **0 / 11**; the 8 at 5/6
**0 / 8**; the other 8 **0 / 8**. The anchors move `ao_alignment` and `constructive_feedback` sharply on the three
questions-only weak replies (0.3 / 0.2) but their weighted totals stay at 0.73, just above the threshold, because they
are accurate, fluent and quote-free; the same pattern appears on several acceptable Socratic replies (0.4 / 0.2–0.4),
so no further floor or threshold is chosen from this data — doing so would be tuning on the hold-out. An offline
replay test asserts the C1 decisions on both committed fixtures.

**Async failure path (R3).** C1 makes a rubric missing any criterion a failed evaluation. In production (async,
`cli/main.py:408`) a failed evaluation is caught at `orchestrator.py:1125-1139`, logged as
`orchestrator_async_coach_failed` at WARNING and **not** turned into a review flag — unlike the sync path's
`_fallback_coach_unreachable` (`:1150-1188`), which flags `decision=fallback`. This stays as is (a failed evaluation is not
a judgement on the reply), and is now stated; the implementation adds a test that an incomplete async rubric logs the
warning and emits no flag. All 46 live verdicts gathered on 18 Oct were complete rubrics.

### Not chosen

* **Making the Coach gate delivery (sync mode):** a latency decision for Rich (the coach waits behind factory work —
  brief item 3); out of scope.
* **Floors on `ao_alignment` / `constructive_feedback`:** the anchors move those scores; a floor would double-count.
* **Changing weights or the threshold:** no evidence the weights are wrong; the scores are.

## Acceptance

* Hermetic suite green; tests updated where they relied on the model's total or on partial rubrics (pad to six).
* New unit tests: recompute overrides the model's total and decision (including model "accept" → computed "revise");
  missing criterion ⇒ malformed; duplicate keeps the lowest; each floor at 0.49 / 0.50; threshold at 0.69 / 0.70;
  feedback filled on revise; the disagreement log carries its values in the message.
* The measured run above meets its bars (detection above baseline on the seen weak replies; 0/11 clean and ≤ 2/8 at 5/6
  revised); both fixtures committed; offline replay test green; the async incomplete-rubric test green.
