# Study Room — Flux prompt pack (sticker sprites)

- **Status**: ready to run. ComfyUI + Flux live on the DGX Spark as **showcard's render box** (confirmed by Rich, 19 July 2026): `COMFYUI_URL` (default `http://host.docker.internal:8188`), graphs `flux1-dev` / `flux1-dev-fast` — see `Projects/appmilla_github/showcard/showcard.yaml` and `Projects/appmilla_github/dgx-spark/RUNBOOK-showcard-cr0.md`. The box wasn't listening on 8188 when probed, so bring it up per the runbook before batching.
- **Companions**: `study-room-cosy-progression.md` (the design, §12 build order / slice-1 asset list) and the "Study Room — Visual Design" artifact page (palettes, art direction, mockups).
- **Goal**: generate the slice-1 bedroom set (26 sprites + 1 backdrop) in one coherent sticker style, then extend per room/pet/event using the same recipe.

## Generation settings

| Setting | Value |
|---|---|
| Model | `flux1-dev` via showcard's render box; use the `flux1-dev-fast` draft graph for style tests and iteration, full `flux1-dev` for finals |
| Resolution | 1024×1024 (sprites), 1408×1024 (room backdrop) |
| Steps / CFG / sampler | drafts: the `flux1-dev-fast` graph as-is; finals: 20–28 steps / cfg ~3.5 / euler |
| Batch | 4 per prompt, pick the best silhouette |
| Post | background removal (`rembg` or ComfyUI segment node) → trim → export PNG with alpha → downscale test at 48 px (silhouette rule) |

## Global style block (prepend to every sprite prompt)

**RATIFIED 20 July 2026** — designer signed off the *detailed storybook watercolour* style after Spark style tests ("the detail is perfect"). The flat-sticker block below it is superseded; the dark-academia block is reserved for a candidate earnable room-makeover set (e.g. Midnight Study).

> Soft watercolor and coloured pencil children's storybook illustration, gentle paper texture, warm cosy academic mood, richly detailed with fine delicate linework, palette of warm cream, honey oak brown, deep indigo blue and soft gold, centered single subject, plain warm cream background, no text, no people, no watermark

Superseded (kept for reference): Flat 2D sticker illustration, cosy warm academic children's-book style, clean vector-like rounded shapes, thin warm-brown outline, one soft top-light, single soft ellipse shadow under the object, plain cream background #F3E7D7, centered single object, no text, no people, no watermark

Palette constraint (append per room): *"palette limited to {room hexes} plus indigo #4B5C92 and gold #B98A2E"*.

- **Bedroom**: #F3E7D7 #C99E72 #4B5C92 #E8B54F
- **Library**: #2F4437 #7A5A3A #B98A2E #E7DCC3
- **Garden**: #BCD8EA #6F9E5F #C46A4A #F2E9D0
- **Lounge**: #8C4A3C #D9B98C #4B5C92 #F0E2CF

Rules from the art direction: silhouette must read at 48 px; **only living things get faces** — furniture never has eyes.

## Slice 1 — bedroom (26 sprites + backdrop)

Room shell:
1. **Backdrop** (1408×1024, no outline/shadow rules): "empty cosy bedroom interior wall and wooden floor, warm plaster wall #F3E7D7, honey oak plank floor #C99E72, simple skirting board, flat 2D children's book style, soft even light, no furniture, no window"
2. "wooden sash window with daytime pale blue sky, honey oak frame"
3. "wooden sash window at night, deep indigo starry sky with a small crescent moon, warm glow at the sill"
4. "simple wooden skirting board strip, honey oak"
5. "soft oval woven rug, muted indigo #4B5C92 with cream border"

Furniture:
6. "single wooden student bed with indigo quilt and one cream pillow, plain and homely" *(the starter bed — deliberately modest; later beds grow grander)*
7. ★ "small wooden student desk with a warm brass reading lamp and one open book" *(the primary object — most important sprite in the app)*
8. "small brass desk lamp with warm glowing shade, switched on"
9. "tall empty wooden bookshelf with three shelves, honey oak"
10–13. "single hardback book spine, {terracotta red #C4453C / amber gold #B98A2E / slate blue #3E6FA3 / leaf green #3F8F5F}, cloth-bound, small blank label" *(competence-artefact spines, one per mastery band)*
14. "plump cosy reading armchair, indigo fabric with wooden legs"
15. "potted fern in a terracotta pot"
16. "small framed botanical print, thin gold frame"
17. "small wooden mantel clock, round brass face, hands only, no numerals"
18. "soft toy teddy bear sitting, honey brown, friendly but simple stitched face"

First pet (cat — pending designer's slice-1 choice of cat vs dog):
19. "small round tabby cat sitting upright, content gentle face, tail curled"
20. "small round tabby cat curled up asleep"
21. "small round tabby cat standing with delighted wide eyes and raised tail" *(welcome-back pose)*
22. "slightly larger fluffier tabby cat sitting proudly" *(evolution stage 2)*
23. "cosy round cat basket bed, cream wicker with indigo cushion"
24. "small felt toy mouse, grey with pink ears"
25. "glass treat jar with fish-shaped biscuits, cork lid"

UI:
26. "single gold coin with an embossed open-book emblem, slight 3/4 tilt"
27. "small gift box, cream with indigo ribbon" *(7-day streak gift)*
28. "small wooden treasure chest with brass trim, closed" *(topic chest)*
29. "ornate but simple rectangular card frame, parchment cream with thin gold border, empty centre" *(fact-card frame)*
30. "square rounded tracker slot tile, soft cream, empty" *(set-tracker slot)*

## Menagerie starters (generate after style sign-off)

- Rooster: "proud Gallic rooster standing tall, russet and indigo-black feathers, red comb, warm friendly eye"
- Bresse hen: "elegant white hen with blue-grey legs and red comb, gentle proud posture"
- Galician pony: "small sturdy chestnut wild pony with shaggy mane, kind eyes"
- Messenger pigeon: "grey messenger pigeon standing alert, tiny brass message tube on leg, gentle proud eye"
- Tortoise: "friendly tortoise with geometric hexagonal-pattern shell in honey and moss tones"
- Axolotl: "pink axolotl with frilly external gills, wide happy face, small bright eyes"
- Snake: "friendly emerald snake coiled in a relaxed spiral, gentle round eye, no fangs"
- Owl: "small tawny owl perched, big amber eyes, feather tufts"
- Tomatina sun-hat (outfit): "small straw sun hat with a ring of tiny red tomatoes around the band"

## Event skin test (December — A Christmas Carol)

- Banner texture: "Victorian Christmas garland of holly, ivy and tiny gold bells across the top of a frame, deep midnight indigo background, gold accents, flat 2D style"
- Robin: "small round robin redbreast perched, cheerful, snow dusting"

## Render-box notes

**The showcard render box is the route** — bring it up per `dgx-spark/RUNBOOK-showcard-cr0.md`, then batch via `POST /prompt`. Fresh-install fallback only if a standalone instance is ever wanted:

```bash
git clone https://github.com/comfyanonymous/ComfyUI ~/ComfyUI
cd ~/ComfyUI && python3 -m venv venv && source venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129   # arm64 sbsa wheels — same family as the other GB10 CUDA venvs
pip install -r requirements.txt
# flux1-schnell (Apache, no HF gate): fp8 checkpoint + clip_l + t5xxl_fp8 + ae.safetensors
# → models/checkpoints (fp8 single-file) or models/unet + models/clip + models/vae (split)
python main.py --listen 127.0.0.1 --port 8188
```

Then batch via the API: `POST /prompt` with the standard Flux workflow JSON, one queue entry per prompt above. Verify VRAM headroom first — the GB10's unified memory is shared with the tutor stack; pause the tutor pair on spark if generation OOMs.
