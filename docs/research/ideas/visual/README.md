# Study Room — visual design assets

All local, all openable in VS Code (PNGs render natively; the HTML opens in a browser / Live Preview). Built from Flux renders on the DGX Spark render box, July 2026.

## Quick-look montages (open these first)
- `01-style-decision.png` — the desk in 3 styles; **detailed storybook watercolour chosen** (designer sign-off 20 Jul 2026). Includes the fixed full-length-quilt bed.
- `02-furniture.png` — the bedroom furniture shortlist (✦ = interactive, ★ = favourite).
- `03-rooms-and-da.png` — Library / Lounge / Garden base backdrops + the dark-academia blend (the Library's late-stage earnable makeover).
- `04-christmas.png` — the first seasonal event: decorated bedroom + lounge.

### Decisions locked (designer, 20 Jul 2026)
- **Style**: detailed storybook watercolour — bright/clean, not muddy.
- **Library**: **Combo A** (`12-library-combined.png`, left card) — angled corner, single left bookcase, brass wall sconces, three-sided half-hexagon bay window seat with simple cushions. FINAL.
- **Christmas bedroom**: **FINAL** = `renders/FINAL-xmas-bedroom.png` (`15-xmas-bed-FINAL.png` shows before/after). Tree-on-desk layout, curved + darker arched headboard, deeper two-blue checkerboard quilt (no white, no ruffle, short posts), watercolour curtains + fairy lights. Made by keeping C's seed and changing only the bed description.

### Revision round (batch 4 — designer notes actioned, 24-step crisper tier)
- `05-revisions-furniture.png` — ivy-on-shelf, empty pet chair, wardrobe (coat+scarf), bowls+mat, cat tree, restyled bedside, tidy festive chair, photobombers removed.
- `06-revisions-rooms.png` — Library wall sconce (no hanging lamp), lounge light aligned to window, two garden variations (shade tree / pond).
- `07-cat-poses.png` — the tabby in five poses (sitting, standing, walking, playing, loaf).
- `08-revisions-christmas.png` — two Xmas bedroom layouts (tree in corner / on desk, lights on curtain pole), lounge window framed + fireplace tidied.
- Batch-4 originals are `renders/r*.png`.

## Library — FINAL (21 Jul 2026, rounds 3–4)
- **`library-FINAL/`** — the agreed set: v1 walls with surgical edits only. Designer rounds (Lilymay): fireplace + bookcase **ceilings recoloured to the same light green** as window/door (deterministic, measured match — signed off); window-seat wainscot **kept exactly as v1** (colour + bay-side panels ruled fine) except the two **edge panels' bottoms completed** (rail + boards, was dissolving into the floor); floorboard **watermark removed**; bookcase-wall **corner wainscot aligned** and window-wall **bay corners aligned** (panels + skirting now wrap all corners continuously, stub blocks gone). Lights kept as v1.
- `21-library-round3.png` — before/after of the designer rounds.
- `shop-light-options/` — the fancy lights (glass lantern, brass sconce) saved as future shop furniture (a swap re-skins all wall-views).
- `20-library-FINAL-changes.png` — before/after of the two changes. `library-turn-demo.html` shows the final walls.
- History: `library-final-v1/` (base), `library-v2-edited/` (light experiments), `18-library-change-brief.png`, `TOMORROW-library-edits.md` (method + status).
- Comparison snapshots: `library-v1-compare/`, `library-v2-compare/`, `17-library-before-after.png`.

## "Turn to face each wall" (Option B) — library prototype
- `library-turn-demo.html` — **interactive**: open in a browser / VS Code Live Preview and click ◀ ▶ (or arrow keys) to turn and face each wall of the same library. This is the ratified room-navigation model (design doc §6.1); 360°/3D are out of scope.
- `16-library-four-walls.png` — the four wall-views as a static filmstrip.
- Final wall set (revised per designer, 20 Jul 2026): `renders/lib-final-wall1-books.png` (kept), `lib-final-win-a.png` (combo-A bay seat, watercolour), `lib-final-fire-a.png` (landscape painting + different plants), `lib-final-door-a.png` (wider, watercolour). All now use the **standard candle sconce**; alt light fittings are shop upgrades (design doc §7).
- Known prototype limitation: walls painted independently drift slightly in wall colour — production needs a locked style/seed or one connected strip.

## The full page
- `../study-room-visual-design.html` — the complete, designed visual-design page (self-contained, ~800 KB). Open in a browser, or VS Code "Live Preview". This is the artifact that would not load over the hosted link.

## Full-resolution renders
- `renders/` — every individual 1024²/1408² PNG with its Spark render receipt name preserved. Source for the finals pass (background removal → true cutout sprites).

## Naming
- `w0*` detailed watercolour · `b0*` dark-academia blend · `c0*` room bases · `d0*` Christmas bedroom · `e0*` Christmas lounge · `a0*` furniture shortlist.

## Related docs
- `../study-room-cosy-progression.md` — the full design.
- `../study-room-flux-prompts.md` — the prompt pack + the ratified watercolour style block.
