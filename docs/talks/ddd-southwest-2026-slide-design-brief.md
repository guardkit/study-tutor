# Claude Design Brief — Planning Cadence Slides for DDD Southwest

**For:** generating slide artefacts in Claude Design (frontend-design skill) to support the planning-cadence angle of the "2026: The Year of the Software Factory" talk
**Talk context:** DDD Southwest, Engine Shed Bristol, 16 May 2026, ~45 min conference slot, audience is senior+ devs / tech leads with mixed exposure to AI-assisted development
**Slide count target:** 2 slides (comparison table + evidence timeline); optional third (re-validation gate template) if the angle expands to 5 minutes
**Companion doc:** `docs/talks/ddd-southwest-2026-planning-cadence-notes.md` — read this first for tone and framing

---

## How to use this brief

Paste the relevant section (one slide at a time) into a fresh Claude Design session. Don't paste all three at once — Claude Design produces better output when focused on one artefact with clear constraints than on a set.

For each slide, the brief gives you:
- The job the slide has to do in the talk
- The content it must contain
- The visual intent
- The technical constraints (dimensions, format, fonts, what to avoid)
- A sample prompt you can lift verbatim

Review after each generation. If the output is 80% right, iterate with a specific change request rather than regenerating from scratch.

---

## General constraints (all slides)

**Format and dimensions.**
- Output: single-file HTML with embedded CSS, no external dependencies. Must render offline.
- Aspect ratio: 16:9 (1920×1080 design canvas, will be projected at conference resolution)
- Exportable to PNG or PDF via browser print — keep it simple enough that `Print to PDF` produces clean output
- No JavaScript animations. Static only. Conference projectors are unpredictable.

**Aesthetic direction.**
- Confident technical, not corporate-deck. Think "engineering-blog screenshot," not "SaaS pitch deck"
- Readable from the back of a 200-seat room — minimum 28pt body text when rendered at slide scale
- Monospace for code-adjacent content (file paths, identifiers); clean sans-serif for prose
- Dark-mode compatible if possible — many conference rooms are dimmed and dark slides read better
- Accent colour sparingly used for emphasis on the recommended/chosen option

**What to avoid.**
- No stock icons of briefcases, rockets, lightbulbs, or checklists. This audience will roll its eyes.
- No gradients that imply "innovation" or "transformation." Flat or subtly textured only.
- No emoji as primary visual elements. A single 🧭 or 🛠️ as a label accent is fine; a grid of emoji is not.
- No AI-generated illustrations of robots or brains. This is a technical talk; the content is the visual.
- No corporate logos (Anthropic, Google, AWS). The talk is vendor-neutral.
- No triumphant "before/after" framing. This is a cadence choice, not a transformation story.

---

## Slide 1 — Cadence Comparison Table

### Job in the talk

This is the slide the audience is looking at when Rich delivers the line *"The cadence isn't the point. The freedom to choose is the prize."* It has to make the three cadence options visually comparable in under 10 seconds of looking, and it has to visibly advocate for the middle column without insulting the other two.

### Required content (verbatim, do not paraphrase)

Five rows, three columns. Header row: "Pure waterfall" | **"Hybrid (this approach)"** | "Pure agile"

Row content:

| | Pure waterfall | **Hybrid (this approach)** | Pure agile |
|---|---|---|---|
| **Plan depth** | All phases fully planned upfront | Next phase full, phase-after sketch, further deferred | Only current phase planned |
| **Momentum cost** | Low between phases | Low between phases | ~10% of budget per phase transition |
| **Speculative waste** | High (later phases against unmeasured reality) | Low (sketches don't commit to day-by-day) | Zero |
| **Re-validation** | Implicit, often missed | Explicit gate per phase transition | Implicit, shorter horizons reduce need |
| **Best for** | Stable requirements, long timelines | Known vocabulary, hard deadlines, measurable risk | Uncertain requirements, short feedback loops |

### Visual intent

- Three-column layout, equal width
- Middle column visually elevated: either a subtle background tint (~10% accent colour), or a slightly heavier border, or a small label "the approach" above the header. Not more than one of these — pick one.
- Row labels left-aligned in a bold sans-serif, weighted heavier than cell contents
- The bold "Hybrid (this approach)" header should be the only bold thing in the header row
- No borders on outer table edges; light horizontal rules between rows is fine; vertical dividers optional
- Slide title above the table: "Cadence as a function of project shape" (36–42pt, not a statement, a framing)
- Small caption below the table, centre-aligned, smaller than body: "Choose per project. Revisit at each phase transition."

### Technical notes

- Table should sit in the upper two-thirds of the slide; leave breathing room at the bottom for the caption
- If Claude Design offers a table-as-cards alternative rendering, try it as a second variant — cards sometimes read better from the back of a room than tables
- Font pairing suggestion: Inter or IBM Plex Sans for body; JetBrains Mono or IBM Plex Mono for anything monospaced (there's nothing monospaced on this slide, but pair consistently with Slide 2)

### Sample prompt to paste into Claude Design

```
Generate a 16:9 conference slide (1920×1080) as a single-file HTML with
embedded CSS, no JavaScript, offline-renderable.

Title at top: "Cadence as a function of project shape" (36–42pt, not bold)

Below: a 3-column comparison table with 5 rows plus headers. The middle
column "Hybrid (this approach)" should be visually elevated — use one of:
subtle background tint, heavier border, or small "the approach" label
above the header. Pick one, not multiple.

Content (verbatim):
[paste the table from the "Required content" section above]

Caption below the table, smaller than body, centred:
"Choose per project. Revisit at each phase transition."

Aesthetic: engineering-blog confident, not corporate-deck. Dark mode
preferred (projector rooms are dim). Minimum 28pt body at slide scale —
readable from the back of a 200-seat conference room. Sans-serif (Inter
or IBM Plex Sans). Single accent colour used only on the middle column.

Avoid: stock icons, gradients implying "transformation," emoji as
primary visuals, before/after framing.
```

### Iteration prompts (if first pass is off)

- "The middle-column elevation is too strong — reduce it to just the 'the approach' label; no background tint, no heavy border"
- "Body text looks smaller than 28pt — increase so it's clearly readable at the back of the room"
- "The accent colour reads as 'this option is marketing-endorsed' rather than 'this option is what we chose.' Desaturate it."

---

## Slide 2 — Four-Artefact Evidence Timeline

### Job in the talk

This is the "put up, don't just tell" slide. Rich has just claimed the hybrid cadence produces four artefacts at four different maturity levels, chosen deliberately. This slide proves it with visible evidence — file paths included, because showing the receipts signals confidence to this audience.

### Required content (verbatim)

Four phases, four maturity levels, arranged left-to-right along a timeline:

**1. Phase 0 — Full Scope + Build Plan**
- *Scope committed:* `study-tutor/docs/research/ideas/phase-0-scope.md`
- *Build plan committed:* `study-tutor/docs/research/ideas/phase-0-build-plan.md`
- *Executes:* 19–25 April 2026
- Maturity: full planning

**2. Phase 1 — Full Scope + Build Plan (one phase ahead)**
- *Scope committed:* `study-tutor/docs/research/ideas/phase-1-scope.md`
- *Build plan committed:* `study-tutor/docs/research/ideas/phase-1-build-plan.md`
- *Executes:* 26 April – 2 May 2026
- Maturity: full planning, written while Phase 0 was still on the whiteboard

**3. Phase 2 — Scope only, build plan deferred**
- *Scope committed:* `study-tutor/docs/research/ideas/phase-2-scope.md`
- *Build plan deferred to:* Thursday 1 May 2026 (during Phase 1)
- *Executes:* 3–17 May 2026
- Maturity: partial planning — day-by-day waits for Phase 1 measurements

**4. Reachy Integration — Conversation starter only**
- *Scope:* none
- *Build plan:* none
- *Conversation starter:* `study-tutor/docs/research/ideas/reachy-integration-conversation-starter.md`
- *Triggered by:* hardware arrival (expected ~25 April) or 4 May go/no-go gate, whichever first
- Maturity: no planning, awaiting external event

### Visual intent

- Horizontal timeline left-to-right across the slide, four "stations" evenly spaced
- Each station is a short stacked block: title → file paths (monospaced) → execution window → maturity label
- Progressive visual "density" from left to right showing decreasing maturity:
  - Phase 0 and Phase 1 stations: solid border, filled interior, both scope and build-plan paths shown
  - Phase 2 station: scope path solid, build plan shown as dashed/ghosted text or struck-through with "deferred" note
  - Reachy station: only conversation starter path shown, block with dashed/outline-only treatment
- Slide title at top: "Four artefacts, four maturity levels — chosen deliberately"
- Small caption below the timeline: "Planning cadence, from `specialist-agent` → `study-tutor`, April 2026"

### Technical notes

- File paths in monospace — this is the load-bearing credibility detail. They must be readable.
- If paths are too long for the block width, break on the last `/` — `study-tutor/docs/research/ideas/` on one line, `phase-1-scope.md` on the next. Don't truncate with ellipsis.
- Dates (execution windows) in a neutral grey; labels ("full planning", "partial planning", etc.) in body weight
- Do NOT use tick/cross iconography. The maturity level is communicated by the visual weight of each block, not by green ticks and red crosses.
- If horizontal timeline doesn't fit well at 1920×1080 with all four stations legible, try a 2×2 grid as an alternative layout — same content, different arrangement

### Sample prompt to paste into Claude Design

```
Generate a 16:9 conference slide (1920×1080) as a single-file HTML with
embedded CSS, no JavaScript, offline-renderable.

Title at top: "Four artefacts, four maturity levels — chosen deliberately"
(36–42pt, not bold, sans-serif)

Below: a horizontal timeline with four stations evenly spaced. Each
station has: phase name (title), relevant file paths (monospace), date
range, maturity label.

The stations progress from "most committed" on the left to "least
committed" on the right. Reflect this visually with decreasing density:
station 1 and 2 solid/filled, station 3 partially ghosted (deferred
content), station 4 outline-only.

Content per station (verbatim):
[paste the four station blocks from "Required content" section above]

Caption below timeline, centred, smaller:
"Planning cadence, from specialist-agent → study-tutor, April 2026"

File paths in monospace (JetBrains Mono or IBM Plex Mono), readable at
back-of-room scale. Break long paths on the last slash rather than
truncating.

Aesthetic: engineering-blog, dark mode. Single accent colour only for
the maturity labels. Do NOT use green tick / red cross iconography —
the maturity level is communicated by visual weight.

Avoid: rocket icons, checklists, stock timeline graphics with arrows
and milestones. This is an artefact list, not a project plan.
```

### Iteration prompts (if first pass is off)

- "The ghosting on station 3 and outline treatment on station 4 is too subtle — they're meant to show decreasing commitment at a glance; strengthen the contrast"
- "File paths are too small; the slide's credibility depends on those being readable from the back"
- "Timeline arrow between stations implies sequential execution, but stations 1/2/3 partially overlap in planning even though execution is sequential. Remove the arrow or replace with tick marks."

---

## Slide 3 (optional) — Re-Validation Gate Template

### Job in the talk

Only needed if the cadence angle expands to 5 minutes and Rich wants to show the concrete artefact that answers "but how do you stop plans ageing badly?" If the angle compresses to 2 minutes, skip this slide entirely.

### Required content (verbatim)

Slide title: "The re-validation gate"

Subtitle: "One-page artefact at each phase transition"

Four stacked panels, each titled and with placeholder body text:

**What held**
*"Assumptions and success criteria from the previous phase that were still true when we looked."*

**What drifted**
*"Things that moved but didn't invalidate anything — adjusted numbers, revised budgets, swapped versions. Acknowledged, noted, moved on."*

**What was falsified**
*"Decisions that were provably wrong in retrospect. Named explicitly. Failure mode added to the lessons doc so the next project doesn't repeat it."*

**What this changes in the current phase**
*"Concrete scope or build plan edits. Made before the current phase's code work begins."*

Small attribution line at the bottom: "Direct response to `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md §8 — 'Decision records must be revalidated at each major milestone.'"

### Visual intent

- Four panels in a 2×2 grid, equal size
- Each panel: bold title, italic one-sentence body
- Consistent visual weight across all four — these are peers, not a flow
- The attribution line at the bottom is quiet but present — it's the receipt for where this came from
- If there's a way to render it that looks like a one-page form template (because that's what it is), lean into that — the slide is showing the artefact, so it can *be* the artefact

### Technical notes

- Keep the panels text-only. No icons per panel.
- If the attribution path is too long for one line, wrap it on the last `/`
- This slide could be generated as the actual `phase-N-validation.md` template — if Claude Design offers to make it look like a filled-in document with light syntax highlighting, that's a nice touch and reinforces "artefact, not concept"

### Sample prompt to paste into Claude Design

```
Generate a 16:9 conference slide (1920×1080) as a single-file HTML with
embedded CSS, no JavaScript, offline-renderable.

Title at top: "The re-validation gate" (36–42pt)
Subtitle below, smaller: "One-page artefact at each phase transition"

Below: a 2×2 grid of four equal panels, each with a bold title and an
italic one-sentence body.

Panel content (verbatim):
[paste the four panels from "Required content" section above]

Small attribution line at the bottom, centred, quiet:
"Direct response to specialist-agent/docs/reference/cross-agent-lessons-
from-specialist-agent.md §8 — 'Decision records must be revalidated at
each major milestone.'"

Visual intent: all four panels equal weight — these are peers not a flow.
If you can render the slide to look like a one-page form template (the
artefact itself), lean into that.

Aesthetic: same dark-mode engineering-blog as previous slides. No icons
per panel. Keep it quiet and document-like.
```

---

## General iteration guidance

If the first pass of any slide is roughly right but off in details, iterate with specific asks rather than regenerating. Good iteration prompts:

- "Make the file paths larger — they're the credibility detail"
- "Reduce the accent colour's saturation by half"
- "The title feels declarative; rephrase it so it reads as a framing not a claim"
- "Drop the icon in the top-left; the slide doesn't need it"

Bad iteration prompts that tend to produce worse output:

- "Make it look more professional"
- "Add visual interest"
- "Make it pop"

If the first pass is fundamentally wrong (e.g. layout doesn't match intent at all), regenerate with a tighter prompt rather than patching.

---

## Export checklist before saving final versions

- [ ] Slide renders offline (disconnect wifi, open the HTML, verify it still looks right)
- [ ] All text readable from simulated back-of-room (zoom out to 50% in browser — if you can't read it comfortably, it's too small)
- [ ] No external font fallbacks. If a requested font isn't present, confirm the fallback is still sans-serif / mono as appropriate.
- [ ] File paths are exactly correct (copy-paste from the `docs/research/ideas/` directory listing to verify)
- [ ] `Print to PDF` in a browser produces a clean single-page PDF per slide
- [ ] Each slide saves as both HTML (for future editing) and PDF (for import into main slide deck)

Final file naming: `slide-1-cadence-comparison.{html,pdf}`, `slide-2-evidence-timeline.{html,pdf}`, `slide-3-revalidation-gate.{html,pdf}` — save to `docs/talks/slides/` (create the directory if it doesn't exist).

---

## Fallback if Claude Design output isn't usable

If after 2–3 iterations per slide the output still isn't conference-quality, fall back to building the slides in whatever tool Rich is using for the rest of the deck (Keynote, Google Slides, Marp, reveal.js — whichever the main talk is authored in). The Claude Design brief above is still useful as a spec for hand-authoring.

Specifically for the comparison table — a native table in the presentation tool will always look cleaner than HTML-rendered-in-a-browser projected on a screen. If Slide 1 is struggling, go native.

Slides 2 and 3 are better Claude Design candidates because the visual hierarchy and decreasing-density treatment are harder to do quickly in a native slide tool.

---

*DDD Southwest slide design brief — 17 April 2026*
*Companion to `ddd-southwest-2026-planning-cadence-notes.md`*
*Execute in Claude Design when slide authoring begins (mid-Phase 2, early May 2026)*
