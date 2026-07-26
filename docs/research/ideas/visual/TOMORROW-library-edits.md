# Library — DONE (21 Jul 2026, round 3)

**Final set = `library-FINAL/`.** Base is v1; only two surgical inpaint edits made, everything else pixel-identical to v1.

## Rounds 3–4 (21 Jul afternoon — Lilymay's notes, final)
1. **Ceiling colour unified — KEPT (designer: "perfect")** — fireplace (was white) + bookcase (was dark mossy) ceilings recoloured **deterministically** (per-column cornice-ink trace, then Reinhard shift of ceiling paint only) to the window/door light green. All four measure within ~7 RGB of (202,196,172). No Flux re-roll, so no drift.
2. **Wainscot: round-3 re-panelling + door-tone match REVERTED** — designer ruled the bay-side panels and the original honey colour were fine as they were. The shipped wall is the **pristine original wainscot** with exactly one shape fix (below) — verified by diff: zero changed pixels outside the two edit zones.
3. **Edge panels' bottoms completed (round 4, the actual designer note)** — the two part-visible FRONT panels at the image edges had bottom frames that ran too low and dissolved into the floor. Their **lower halves only** were inpainted: bottom rail at the neighbour's height + plain boards below, same honey colour (hybrid: seed 42 left + seed 91 right; masks start mid-panel so cap rail + panel tops are untouched).
4. **Watermark removed** — the "NO2 …" pseudo-URL text on the window wall's floorboards (pre-existing v1 artifact) inpainted away.
5. **Bookcase-wall corners aligned (round 5)** — designer's screenshots showed panels/skirting jumping ~20px across both room corners of the bookcase view. Both corner zones re-rendered **as single regions spanning the corner** (masks seamed in the stile gaps at x360/x1058 — mid-panel seams break skirting lines; learned the hard way), seed 42. Rails now meet at the corner and the skirting wraps continuously. Door-wall corners checked: already fine.
6. **Window-wall bay corners aligned (round 6 — the corners the designer had actually pointed at; round 5's screenshots were these, misread as bookcase)** — same corner-spanning treatment either side of the seat: framed panel + pier boards now share one base line, one skirting wraps each corner, floating stub gone. Seams at the stiles (x190/x1218); cushions/armrests/seat box pixel-protected (verified). Seed 123 shipped — seed 42 looked better at 1x but FAILED the seam judge (broken skirting + ink spike); trust the zoomed judge over the eyeball.
7. **Skirting made continuous edge-to-edge (round 7)** — the corner runs still ended mid-wall in chamfered stub caps (designer's third catch). Base bands x0-200 and x1200-1408 re-rendered; one unbroken skirting now runs the full wall like the door/bookcase walls. Seed 123 again (seed 42 failed judge again — box artifact). Window wall wainscot now fully consistent.
8. **Bay-side panels restored to the originals (round 8)** — designer flagged the r6 panels as "odd, not like real life" (they'd grown ~40px too tall, bottoms crowding the skirting). After three failed re-render/warp attempts (all judge-rejected: guide leaks, seam smears, cushion clips), the fix was the simple one: **composite the designer-approved ORIGINAL panels back** from the pre-round-3 file, with the plank strokes below each rail digitally extended to bridge onto the approved skirting. Deterministic; judge pass. First attempt's feathered paste smudged ghost lines onto the skirting cap (designer caught it — "skirting broken again"); corrected by stopping the paste hard above the cap: final diff = zero pixels in the skirting band (y>843), ~3px clean feather at zone edges. **Lessons: when the designer says "it was fine before", restore the before — don't re-create it. And never let a paste feather cross a signed-off boundary.**
9. **Skirting steps at round-boundary joints levelled (round 9)** — designer: "skirting broken / no improvement". Root cause found by tracing the cap line across the WHOLE wall: height steps at the joints BETWEEN repair rounds (x~195, x~1215) — inherited flaws each round's own diff scored as "no change", so no judge ever caught them. Two small skirting bands re-rendered dead level (mix: seed 91 left + seed 123 right), green speck removed. **Lesson: per-round diffs can't see inherited flaws — periodically verify whole-wall invariants (one continuous cap line) against the room, not the previous round.** `skirting-check-spots.png` (A–D lettered crops) added so the designer can reference spots by letter.
10. **Panel leans plumbed (round 10)** — designer: panels "still mis-aligned". Plumb-line overlays + robust line fits found per-panel leans from the patchwork of rounds: left pier leaning ~-8px, left restored panel's frame bowed mid-height; most others within ±4px (hand-drawn character, left alone). Fixed deterministically (per-row horizontal remap onto true verticals, bottom-anchored). A first pass also warped the right pier, but its "leaning edge" was actually the cushion's shadow — the warp dragged cushion pixels and was caught in the before/after sheet, then REVERTED (right pier untouched, cushions verified 0 px changed). **Lesson: shadows slope legitimately — never warp a tracked line without confirming it's joinery, and keep cushion boxes out of every warp/diff-allowance zone.**
11. **Left-wall top rails aligned (round 11, Rich's catch)** — panel TOP rails stairstepped 646→676→701 along the left wall (each repair round inherited its own height). Warp attempts folded frame corners at 20-30px moves → re-rendered the front+edge panels via masked Flux instead (seed 123; seeds 42/91 hallucinated a post in the 6px gap BETWEEN the two mask zones — leave no unmasked slivers between adjacent zones). Tops now run in one gentle line; diff-gated ship (0 px outside zone). Right wall ~12px steps deemed acceptable pending Lilymay. **Lesson: deterministic warps are for ≤10px nudges; full-panel re-render with aligned neighbours as context is the tool for big geometry moves.**
- Verified by adversarial judge panels each round (4-judge, 2-judge, 1-judge — final: pass, zoom-only nitpicks).
- Before/after: `../21-library-round3.png`. Render receipts: `../renders/r3-*.png` (superseded), `../renders/r4-*.png` (shipped).

## Open for Lilymay / Rich
- **Door wall colour** (teal vs sage) — still deferred by Rich.
- Door wall floor has a small cursive artist-signature squiggle (bottom-right) — same artifact class as the removed watermark; clean in a future pass.
- Lesson for future rounds: "front panels" = the ones at the image edges, furthest from the window. Confirm which panels before masking.

## Final four walls (surgical inpaint edits on v1)
1. **Bookcase wall** — v1 + unified ceiling.
2. **Window seat wall** — v1 + wainscot → **rectangular raised panels** (darker, crisp/distinct) + unified ceiling. Seat, cushions, v1 lights untouched.
3. **Fireplace wall** — v1 + **fire → soft natural flames** + unified ceiling. v1 lights/curtains/bookcases/painting/plants untouched.
4. **Door wall** — v1 + unified ceiling.

**Ceiling unification (21 Jul):** all four now share a **light sage-green ceiling + white crown-molding cornice** (fireplace-style trim, door/window-style colour). Cornice styles are close but not pixel-identical across walls (independent inpaints) — fine, but a candidate for a final consistency pass.

## Decisions (Rich, 21 Jul)
- **Lights**: keep v1's candle sconce on all three rooms (already consistent). The fancy new lights are **shop options**, saved in `shop-light-options/` (`light-glass-lantern.png`, `light-brass-sconce.png`) — a light swap re-skins every wall-view at once (design doc §7).
- Turn-demo (`library-turn-demo.html`) refreshed with the FINAL set. Before/after of the two changes: `20-library-FINAL-changes.png`.

## Method (reuse for other rooms)
Surgical **masked Flux inpainting** on the Spark, then composite the masked region back onto v1 so out-of-mask = pixel-perfect. Tools: `inpaint_render.py` (on box `/tmp/`), PIL masks, `Image.composite(inpaint, v1, mask)`.

## Still open / deferred
- **Door wall colour** (teal vs the others' sage) — deferred by Rich.
- Faint model "signature" watermark on a couple of walls — crop at final sprite stage.
