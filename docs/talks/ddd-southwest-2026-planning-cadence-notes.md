# DDD Southwest Talk Notes — Planning Cadence Angle

**Talk:** "2026: The Year of the Software Factory"
**Venue:** DDD Southwest, Engine Shed, Bristol
**Date:** 16 May 2026
**Speaker:** Rich Woollcott (Appmilla)
**Status:** Talk notes — drafting material for one or two slides within the wider talk

---

## Purpose of these notes

The broader DDD Southwest talk argues that traditional PM tooling (Jira, Linear) is a category error for AI-assisted development — the planning layer and the build layer should collapse into one outcome-driven pipeline. Somewhere in the middle of that talk, an audience will ask (or internally wonder): *"Don't these agent-generated plans just hallucinate the future? Aren't you building against plans that age badly?"*

The planning-cadence doc written during the Study Tutor build (`study-tutor/docs/research/ideas/planning-cadence-hybrid-approach.md`) was written partly in response to that implicit objection. It documents, with live evidence from two back-to-back builds (specialist-agent + Study Tutor), a deliberate cadence choice that's neither waterfall nor agile.

These notes capture the talk-specific framing — what to say out loud on stage, what evidence to show on the slide, what to cut if time is short.

---

## The core argument, in one slide's worth

**The objection addressed:** *"Your software factory produces plans too far ahead — they hallucinate the future, then you build against plans that age badly."*

**The answer:** The factory can produce any granularity; the human operator chooses the cadence. Here's the one chosen for Study Tutor — a 31-day hackathon build on a known architectural vocabulary — and why.

**The named pattern:** write the next phase in full, sketch the phase after that, defer anything further, re-validate at each transition.

**The evidence:** four artefacts at four different maturity levels, chosen deliberately.

1. Two scope + build-plan pairs already committed (Phase 0 + Phase 1) — full planning
2. One scope-only sketch (Phase 2) — partial planning, build plan deferred
3. One conversation starter (Reachy integration) — no planning, triggered by external event

**The bridge back to the main thesis:** the planning artefact is *directly machine-readable* (feeds `/system-arch`, `/system-design`, `/feature-spec`) and *directly human-readable* (narrative, decisions, re-validation gates). The artefact doesn't need to be translated through a ticket system; the ticket system can be derived from it. That's why Jira-style PM tools are a category error for this shape of work.

---

## Why this is worth a slide (or two) specifically

Three reasons this lands with a DDD-flavoured audience:

**One.** Most devs in the room have lived through both pure-waterfall pain (early-2000s requirements docs that were wrong before kickoff) and pure-agile pain (sprint planning that consumes a day every two weeks, no compounding context). They'll recognise the failure modes immediately, and they'll recognise that the answer is usually "something in between, decided deliberately."

**Two.** The cadence choice is *specific to the shape of the project*, not universal. Known architectural vocabulary + hard deadline = hybrid. Unfamiliar vocabulary + soft deadline = thinner planning. That reframing — "cadence as a function of project shape, not of methodology fashion" — is the kind of nuance DDD audiences tend to appreciate.

**Three.** The re-validation gate is the interesting bit. Pure waterfall skips it; pure agile doesn't need it because horizons are short. The hybrid *needs* a named gate, and naming it turns a generic lesson ("check your assumptions periodically") into a concrete artefact (`phase-N-validation.md`). That artefact-first move is very on-brand for the software-factory thesis.

---

## The comparison table (slide-ready)

Drawn from the end of the planning-cadence doc. Rendered as a single slide:

| | Pure waterfall | **Hybrid (this approach)** | Pure agile |
|---|---|---|---|
| Plan depth | All phases fully planned upfront | Next phase full, phase-after sketch, further deferred | Only current phase planned |
| Momentum cost | Low between phases | Low between phases | ~10% of budget per phase transition |
| Speculative waste | High (later phases against unmeasured reality) | Low (sketches don't commit to day-by-day) | Zero |
| Re-validation | Implicit, often missed | Explicit gate per phase transition | Implicit, shorter horizons reduce need |
| Best for | Stable requirements, long timelines | Known vocabulary, hard deadlines, measurable risk | Uncertain requirements, short feedback loops |

The middle column is the one I'd highlight on stage. The "best for" row is the one that turns this from a methodology recommendation into a diagnosis question.

---

## The evidence slide

Four phases, four maturity levels, chosen deliberately. This is the "put up, don't just tell" slide.

- **Phase 0** — scope + build plan committed, executed weekend of 19–20 April 2026. Full planning.
- **Phase 1** — scope + build plan committed, executes weekend of 26–27 April 2026. Full planning, written while Phase 0 was still on the whiteboard.
- **Phase 2** — scope only committed. Build plan scheduled for Thursday 1 May, written during Phase 1's execution once Phase 1's Graphiti latency spike and Coach tuning outcomes are known. Partial planning.
- **Reachy integration** — conversation starter only. No scope, no build plan. Triggered by hardware arrival (~25 April per 90-day delivery from order) or by 4 May go/no-go gate, whichever comes first. Zero planning.

For the visual: a simple horizontal timeline with four rows showing the maturity level of each, colour-coded. Easy to read from the back of the room.

If there's time: add the source pair for each artefact at the bottom of the slide — `study-tutor/docs/research/ideas/phase-0-scope.md`, `.../phase-0-build-plan.md`, etc. This is where audience members who want to verify the claim can go afterwards. Putting the paths on the slide signals confidence in the receipts.

---

## The re-validation gate as the interesting move

If only one concept from this angle lands with the audience, make it this one.

**The lesson it comes from:** in the specialist-agent build (the project preceding Study Tutor), an architectural decision was captured in `TASK-DEPG-A3F2` claiming "near-full parity" for Product Owner handlers over MCP. That claim was written during Phase 2 planning based on the adapter shape visible at the time. It stayed in place through three subsequent milestones. In April 2026, a deployment walkthrough (`TASK-REV-B8E4`) falsified it in specific enumerable ways — architect handlers were wired but Orchestrator methods were missing, PO handlers hard-coded provider="claude", tool descriptions promised fire-and-forget but the implementation was synchronous. None of the workflow layers between "plan written" and "plan falsified" caught it until the walkthrough forced a re-read.

The lessons doc that came out of that build (`specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` §8) states it as: *"Decision records must be revalidated at each major milestone."*

**The artefact response:** at each phase transition in Study Tutor, produce a `phase-N-validation.md` with four headings — "What held / What drifted / What was falsified / What this changes in the current phase." One paragraph each.

**Why this matters for the talk:** it turns a generic lesson into concrete process. It's the kind of thing you can show on a slide as a four-row template and say "here's what this looks like in practice." It's also the kind of thing that pure-waterfall culture skips (plans are assumed correct until a walkthrough forces otherwise) and pure-agile culture doesn't need (horizons are short enough that today's plan is today's reality). Hybrid cadence *needs* the gate; naming it is what keeps the cadence honest.

---

## Bridging back to the main thesis

The line that carries the audience from this angle back to the broader Year-of-the-Software-Factory argument:

*"The cadence isn't the point. The point is that when your planning artefact is machine-readable — when `phase-1-scope.md` feeds `/system-arch` directly — you can choose your cadence deliberately rather than inheriting one from a PM tool. Jira-as-category-error isn't about Jira being bad. It's about the planning layer and the build layer being fundamentally the same layer when AI is doing the work. The hybrid cadence is just one choice within that; the freedom to choose is the prize."*

That's the two-sentence payoff. Everything above it is evidence.

---

## Speaking points, if the cadence angle is 5 minutes within a 45-minute talk

If time is tight, here's the narrative compression — roughly 400 words delivered spoken:

> "I want to flag something that fell out of the build when I was preparing this talk. Every time I describe the software factory to another engineer, they ask some version of: 'Don't your agents just hallucinate plans that age badly?' And that's a fair objection, because I've done both things — built against plans that were stale before we started, and built in pure-agile mode where every sprint planning meeting ate a day we didn't have.
>
> So when I was scoping the Study Tutor build — 31 days, hard deadline, known architectural vocabulary — I had to make a cadence choice consciously. Not inherit one. And the answer wasn't waterfall, wasn't agile. It was this.
>
> [show slide]
>
> Write the next phase in full. Sketch the phase after that — scope only, no day-by-day plan. Defer anything further. And add an explicit re-validation gate at each transition, because the single biggest lesson from my previous project was that decision records must be revalidated at each major milestone, and I didn't have that as a named artefact.
>
> Here's what that looks like concretely. [show evidence slide] Phase 0, committed, weekend of April 19. Phase 1, committed, Phase 1 code written with Phase 1B's shape in mind — that's free context-carrying you lose in pure agile. Phase 2, scope committed, build plan deferred until Phase 1's measurements are in — that's speculative waste you lose in pure waterfall. Reachy integration, conversation starter only, triggered by hardware arrival. Four maturity levels, chosen deliberately.
>
> And at each transition, a four-paragraph validation doc. What held. What drifted. What was falsified. What changes. That's the gate.
>
> The cadence isn't the point. The point is that when your planning artefact is machine-readable — when `phase-1-scope.md` feeds `/system-arch` directly — you can choose your cadence deliberately, based on the shape of the project. Hard deadline plus familiar vocabulary gets you the hybrid. Soft deadline plus unfamiliar vocabulary gets you thinner planning. Jira-as-category-error isn't about Jira being bad. It's about the planning layer and the build layer being fundamentally the same layer when AI is doing the work. The hybrid cadence is one choice within that. The freedom to choose is the prize."

Seven hundred–ish spoken words, ~5 minutes at conference pace.

---

## What to cut if time is tighter

If the cadence angle gets compressed to 2 minutes:

- Drop the re-validation gate detail. It's the interesting move but it's second-order.
- Drop the spoken comparison to pure-agile cost. Keep waterfall contrast because it's the more common failure mode the audience lives with.
- Keep the evidence slide — four artefacts, four maturity levels — because it's the empirical bit.
- Keep the bridge sentence at the end.

If it gets compressed to 1 minute (60 words):

> "One thing that fell out of the build: my agents can produce plans at any granularity. So I have to choose. For Study Tutor — 31 days, known patterns — I chose hybrid. Next phase full, phase-after sketch, validation gate at each transition. Four artefacts, four maturity levels, on purpose. That freedom to choose cadence — *that* is what makes Jira-style tools a category error."

---

## What to cut if the cadence angle doesn't land in rehearsal

The evidence slide stands alone. If the spoken argument feels thin in rehearsal, cut straight to the evidence slide, let the audience read the four rows, and move on. "Four phases, four maturity levels, chosen deliberately" is self-explanatory for this audience. The narrative wrap is nice but not essential.

---

## Things *not* to say on stage

- Don't claim the hybrid cadence is better than waterfall or agile universally. It's better *for this project shape*. Get that caveat in explicitly.
- Don't disparage Jira or Linear by name. "Ticket-based PM tools are a category error for AI-assisted work" carries the argument without inviting a "well actually" about Jira's strengths.
- Don't overload the slide with the full planning-cadence doc. The comparison table is the slide; the 14KB doc is the footnote for the audience to read after.
- Don't use the word "agile" without qualifying it. Everyone means different things by it. "Short-horizon iterative planning" or "sprint-based planning" lands more cleanly.

---

## Post-talk follow-up

When someone comes up after the talk asking about this specifically (and someone will), the one-liner hand-off is:

*"The full cadence doc is in the Study Tutor repo — `docs/research/ideas/planning-cadence-hybrid-approach.md`. The rationale for this specific project shape is at the end. If you want the backstory, the lesson it responds to is in `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` section 8."*

Two repos, two file paths. Short enough to write on a business card.

---

## Related artefacts in this repo

- `docs/research/ideas/planning-cadence-hybrid-approach.md` — the full approach doc, from which the slide material draws
- `docs/research/ideas/phase-0-scope.md` + `phase-0-build-plan.md` — evidence of "next phase in full"
- `docs/research/ideas/phase-1-scope.md` + `phase-1-build-plan.md` — same, one phase ahead
- `docs/research/ideas/phase-2-scope.md` — evidence of "sketch only"
- `docs/research/ideas/reachy-integration-conversation-starter.md` — evidence of "no planning yet"
- `docs/research/ideas/decisions-log-2026-04-17.md` — the do-not-reopen discipline that complements the cadence

---

*DDD Southwest talk notes — 17 April 2026*
*Source conversation: Study Tutor planning session, 17 April 2026*
*Slot in the wider talk: likely mid-talk, after the main "Jira-as-category-error" argument, before the "what do you do with the freedom" wrap*
