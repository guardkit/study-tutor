# The Study Room — a cosy progression layer (rooms, pets, shop, events)

- **Status**: idea / reviewed design — not yet a feature spec
- **Designer**: Lilymay (the student). Captured and structured in conversation with Claude, 19 July 2026 (multiple design sessions; cross-subject festival events added after the multi-subject ratification).
- **Reviewed**: 19 July 2026 by a three-lens panel (design-principles, motivation-psychology, feasibility); all confirmed issues folded in. Panel headline: the §9 exotic-pet prerequisite chains are the strongest mechanic ("wanting the tiger *is* wanting to finish the poetry anthology"); the original XP-doubling Focus Charm was the weakest and was reshaped to coins. Session-2 additions (§6 home screen, §10 album, §11 events/crystals, lifetime-days rewards) reviewed the same day by a two-lens follow-up pass; all confirmed issues folded in.
- **Relates to**: `docs/gamification/design.md` (live W1+W2 economy), FEAT-PO-008 (adaptive challenges / boss battles), FEAT-PO-009 (progress dashboard), the deferred daily-challenge / weekly-quest designs (§2.2–2.4), and design.md §12's Phase-3 multi-subject expansion.
- **Multi-subject**: ratified as a load-bearing requirement, not a later port, by Rich on 19 July 2026 — see §2 "One home, many subjects". English is the first content pack, not the identity of the system.

## 1. Vision

Progress in the app today is numbers: XP, levels, streaks, badges. This layer turns progress into a **place**. Studying earns coins; coins buy furniture, accessories, and pet things in a shop; those decorate rooms that start as a bedroom and grow — over a whole revision season — into a home you built with your own work. Pets live in it. **The room is the first thing you see when you open the app** (§6): the app *is* the room, with studying, missions, and everything else reached from it.

Designed moments across the season:

- **Day one is not empty** (endowed progress): the bedroom starts with **a standard single bed** (designer's choice) — and beds are a progression line of their own, growing larger and more detailed as you level, so even the very first object tells the story later. Every furniture-set tracker opens at 1-of-6 ("your pet found the first piece").
- **The April open house** (season finale): once, before exams, the app shows the September room next to the finished one. The room *is* the progress report.
- **Postcards** (designer-approved): exportable snapshots of your room to show friends or family "so they too can see how much progress you've made" — entirely student-initiated, via the OS share sheet, no in-app social surface.

The designer's build priority: **the room comes first**, "that way you can start seeing your hard work first."

## 2. Why it fits the existing design principles

The live gamification system (design.md) is built on: single student, no social competition, no guilt, no punishments, nothing ever taken away, XP as an honest permanent record of study, no real money, no predicted grades. This layer is compatible by construction:

- **Self-expressive, not competitive** — a room of one is (unlike a leaderboard of one) still meaningful. Postcards are shown *by* the student, never published.
- **Nothing is ever lost.** Furniture, pets, friendship, trophies, event items only accumulate.
- **XP is never spent, never multiplied, and never earned outside study.** Coins carry the shop; event minigames pay coins/cosmetics, never XP (§11). The ratified §13.1 bands are untouched.
- **No real money, ever.** Everything is earned.

### One home, many subjects (multi-subject by design)

Ratified 19 July 2026 (Rich): the app is multi-subject — the model has already been validated with per-subject prompts. This layer is therefore split into a **subject-neutral core** and **per-subject content packs**:

- **Subject-neutral core — one of each, shared across all subjects**: the student, the home, the rooms, the pets, the coin purse, XP/levels, streaks, weekly consistency, lifetime days, the base shop catalog, chests, memory crystals, the album. A qualifying session in *any* subject pays the same coins and counts the same day; there is one level ladder and one flame. Splitting these per subject would fragment motivation and punish breadth — the room shows the *whole student*.
- **Per-subject content packs — one per subject, plugged into the same engine**: mastery/exploration/growth achievement catalogs (the live English W2 catalog is the first instance of this pattern, not a special case), topic chests (topics namespaced by subject), competence artefacts (each subject grows its own shelf), exotic-pet prerequisite chains (§9's English chains are the template — every subject gets its own creature), subject-flavoured furniture sets, and event skins (§11's *A Christmas Carol* is English's flagship; other subjects contribute their own seasons).

Nothing in the English examples in this doc is structural — wherever it says "Macbeth" or "poetry", read "a content-pack entry".

Study → XP (levels, badges — the permanent record) **+ coins** (spendable) → shop → rooms, furniture, pets → visible, growing proof of work → reasons to come back tomorrow. Seasonal events (§11) add periodic novelty without touching the core loop.

## 4. Coins (second currency)

Earned by studying, its milestones, and (capped) event play — no other faucets. Sketch values — tune against the income model in §15 before speccing:

| Source | Coins (sketch) |
|---|---|
| Qualifying session (mirrors XP bands 60/120/180) | 10 / 20 / 30 (Phase-1 launch boost: 15/30/45 until challenge/quest income ships, then revert) |
| **Weekly consistency: studied 5 days in any rolling 7** (repeatable — the primary consistency income) | 75 |
| **Lifetime study-days milestones 25/50/100/150 days; 200 long-horizon** (designer's idea — total days ever studied, not consecutive; a streak that can never break. A "day" = a London date with ≥1 settled qualifying session; supersedes the generic achievement-coin rule; these badges award 0 XP) | 100 / 200 / 400 / 600; 1000 at 200, + trophies at 100 and 200 (§10). 150 is the season capstone at a healthy 5-day pace; 200 is a multi-season (Year 10+11) milestone, never a this-season target |
| Streak milestones 3/7/14/30/60/100 days (once per milestone; **supersedes** the generic achievement-coin rule for the six streak badges) | 50 / 100 / 200 / 300 / 400 / 500 (7-day also gives a gift box item) |
| Achievement unlock (all non-streak badges) | badge XP ÷ 2, rounded to 5 |
| Level-up chest | level's XP span ÷ 6 (≈20c at Level 2, ≈600c at Level 15 — keeps pace with the curve) |
| Daily-challenge sweep / weekly quest (when built) | 30 / 100–200 |
| Furniture set completion | +200 + exclusive centrepiece item |
| Event minigames & event missions (§11) | small coin amounts + event items; never XP. Minigame coins cap per London day (≤ half a short session's coins) — a qualifying session always out-earns a day of minigame play |

Calibration, stated honestly (panel correction): **sessions pay ~6 XP per coin; milestones intentionally pay burst bonuses at 2–3× that rate.** The weekly-consistency and lifetime-days rewards exist because long *consecutive* streaks are unreachable for a healthy student who rests weekends — a 5-day week must be first-class, not a failure mode.

Design rules (ratified in conversation + review):

- Set completion pays **coins + an exclusive item, not XP** — XP stays something only *studying* can produce.
- **Pacing invariant**: a 5-session week always affords at least one shop item; first furniture within 3 sessions of starting.
- **Subject-neutral earning** (§2): session coins, weekly consistency, and lifetime days pay identically for any subject — the economy never prefers one subject over another.
- All day/week/event arithmetic uses **Europe/London** per design.md §13.1 D6, via the existing `london_date` helpers.

## 5. Rooms

- Start: **Bedroom** (Level 1, with the starter bed).
- More rooms at level milestones, thematically matched to the level titles: **Library** at Level 6 (*Scholar*), **Garden** at Level 9 (*Expert*), **Comfy lounge** at Level 12 (*Virtuoso*).
- Each room has 2–3 **expansions** gated by total-XP/session thresholds and bought with coins — expansion is both *earned* (study) and *chosen* (spend). Expansions are the intended **large late-season coin sinks**.
- Fully customisable: wallpaper, flooring, placement. The student **chooses which room is on the home screen** and switches with one button (§6) — "this allows you to fully customise and make the app yours."
- Rooms belong to the **student**, not to subjects (§2) — subject flavour arrives as furniture sets and artefacts, never as "the Maths room". The Library unlocking at *Scholar* is a level reward, not an English reward.
- **Dark-academia Library makeover** (designer decision, 20 July 2026): the ornate dark-academia furniture style (Spark style test, set 2) is the **Library's late-stage earnable makeover** — the watercolour base world stays warm and legible everywhere; candlelit velvet is a high-level Library transformation you earn.
- **Competence artefacts** (panel suggestion, strongly endorsed): some room items are earned displays, not purchases — a bookshelf that gains a labelled spine per topic mastered (**per subject: each subject grows its own shelf**), a trophy per completed mission chain, a framed quotation per Quote Champion/Master milestone. The decor then *means* something learned, which is the best defence against rewards hollowing out the studying itself.

## 6. The room is the home screen (designer's UI architecture)

The app opens straight into your chosen room. Layout as designed:

- **Top HUD**: level + XP progress to the next level; coin balance; streak flame. (All but coins are already on the wire: `level_number`, `xp_into_level`, `xp_to_next_level`, `streak_days`; the HUD should consume the existing `ProgressStore`, since the flame's "alive today" state is app-local and would be lost on a fresh fetch path.) **HUD kindness states** (review): the front door shows only numbers that grow — the flame never renders zeroed, dimmed, at-risk, or countdown states here; after a streak reset the slot leads with lifetime days studied (which cannot break) until a new streak reaches 3. The celebration sheet and progress page keep their richer states; the *front door* never opens on a loss.
- **Room switcher**: one button to flip between unlocked rooms.
- **Mission pop-up (left edge)**: your main mission (e.g. the snake chain — "2 of 4 ready 🐍") with a *more* button expanding to all active missions. This is the near-achievement `{progress, target, hint}` shape, promoted to the front door. (Until the slice-2 quest lifecycle ships, the pop-up can only surface the existing top-3 near-achievements — a slice-1 spec must not promise chains.)
- **Menu button (top)** opening:
  - **Continue previous session / start a new one** — and, review fix so studying is genuinely one tap away: **tapping the desk in the room starts or continues a session**. The room's furniture includes the reason the room exists; the menu entry is the secondary path.
  - **Missions** — all current missions plus daily/weekly quests.
  - **Achievements** — every badge, plus **total study time** and **total days studied** (lifetime, not streak — designer's idea, with its own reward track §4) "so you can see them all and watch the list grow."
  - **Shop** — multiple pages (furniture, pet toys, treats, wallpaper…).
  - **Boss battles** — appears once unlocked at Level 8.
  - **Album** (§10) — postcards, pet galleries, trophy room, profile.
  - **Archive** (§11) — completed events and what you earned from them.

Staging note (feasibility): the current home screen is the session list + progress card, pushed via Navigator 1.0 — **no tab/navigation shell exists yet**, so "ship as a tab first" includes building that shell and rehoming the current home (session-list fetch, resume/start guards, auth routing, pull-to-refresh) inside it — a MODERATE cost item of its own (§14). The room then **becomes the front door once the renderer matures** — the end-state above is the designer's intent, not slice 1.

### 6.1 Room presentation — flat 2D with "turn to face each wall" (ratified 20 July 2026, Rich)

The room is presented as **flat 2D painted scenes**, not 3D and not a 360° panorama. Full-3D and 360° are **explicitly out of scope — now and as a future phase** (designer's decision: not wanted). Keeping it 2D is what preserves the hand-painted watercolour identity (the ratified §12-build style) and keeps the room cheap and buildable.

To give a sense of *being in* the room without any of the 3D cost, each room supports **"turn to face each wall"**: 2–4 fixed painted views of the same room from different facings, with on-screen left/right controls that snap between them (discrete 90°-ish turns, not smooth rotation). It is the affordable middle ground between a single static wall and a 3D scene, and it reuses the exact Flux painting pipeline that produced all the concept art.

Implications for the build:
- Each room ships **N wall-views** (start with 2–4). The Library is the prototype (see `docs/research/ideas/visual/` — `16-library-four-walls.png` and the local `library-turn-demo.html`).
- The **walls must read as one continuous room** — same wall colour, floor, wainscot, sconces across views. In production, either paint the wall-set with a locked style/seed, or paint one wide connected strip and slice it, so independent renders don't drift.
- `room_layout` (§14) gains a **facing** dimension: furniture placement and the active-pet position are per-wall-view, and the layout blob keys on `(student_id, room_id, wall)`.
- Interaction: a simple **◀ / ▶ turn control** on the room screen cycles the wall-views; the desk-tap-to-study affordance (§6) lives on whichever wall the desk is placed.
- 2.5D parallax (subtle layer-shift on device tilt) remains an optional later polish that composes with this; it was considered and is *not* part of the ratified plan.

## 7. Shop, furniture, and sets

- Shop sections unlock with levels — **added alongside** the existing `LEVEL_UNLOCKS` entries via a design §3.2 patch (a level may unlock both a feature and a shop range; existing promised features are never renamed or replaced).
- Price bands (sketch): small decor 50–150, furniture 200–500, wallpaper/flooring 300, pet toy 100, pet treat 20, pet bed 250. Beds form an explicit upgrade line from the starter single bed (§1).
- **Furniture sets** (designer's idea): themed series of 5–6 pieces (e.g. *Midnight Study*, *Spring Garden*), tracker endowed at 1-of-6. Completion pays the set bonus (§4).
- **Exclusive items** (designer's idea): certain pieces only come from quests, mission chains, topic chests, pet friendship, or events — never the shop. **Recurrence rule (kindness)**: every exclusive's source recurs — quests rotate back, events replay via memory crystals (§11). "Available this week only, then never again" is banned — a missed week must never be a permanent loss.
- **Shop permanence**: items never leave the catalog permanently and prices never rise. A weekly rotating "featured shelf" keeps the shop fresh through the back half of the season, but rotation copy says "back soon", never "last chance".
- Furniture/decor are **duplicable** (two matching armchairs is a legitimate lifestyle choice) — quantity, not one-of-each; exclusives and pet gear are one-of-each.
- **Light fittings are a shop category** (designer idea, 20 July 2026): a room ships with a **default** wall light, and alternative fittings are buyable swaps that re-skin every wall-view at once. For the Library: **default = the ornate single-candle brass sconce** (bookcase-wall style); **shop alternatives = the brass dome/reading lamp** (fireplace-wall style) and the **twin-candle shaded sconce** (combo-A style). Because a swap changes all wall-views (§6.1) together, lights are a cheap, satisfying way to restyle a whole room with one purchase.

## 8. Pets and friendship

- First pet at **Level 5** (choose cat or dog — they fit the rooms). Second slot at Level 10, third at 15.
- **Friendship level** per pet, only ever rises. **Invariant: a session must always out-earn a day of treats.**
  - +3 per qualifying session studied "together" (active pet)
  - +1 for the first treat each London day (further treats trigger animations only — treats stay a ritual, not an engine)
  - passive trickle while the pet's **favourite items** (designer's idea) are placed in its room — discovering favourites is part of the fun
- Friendship milestones (10/25/50/100): new poses, wearable accessories, and — designer's idea — a **unique furniture piece the pet gives you**, unobtainable any other way.
- **Subject milestone outfits** (designer's idea): significant milestones in a subject — meaning **one-time catalog achievements in that subject's pack** (mastery/exploration/growth), never raw session counts — award an **outfit or accessory for that subject's animal**, never sold in the shop (a §7 exclusive; it **stacks** with the badge's normal §4 coin payment, being an item, never a coin or XP source). Each grants a one-time friendship bonus (sketch **+3 — never more than one session's worth**: outfits decorate the mascot, they don't level it; banked server-side at earn time, with first-wear kept as a client animation moment) and **carries a fun fact** about what it depicts: the Spanish pets earn a tomato-themed accessory with facts about *La Tomatina*, the Buñol tomato festival — itself on-spec for the languages customs-and-festivals topic. **Fact-card copy is curriculum content**: owned by the subject content pack and reviewed to the same accuracy bar as tutoring material — a wrong fact in a reward is still a wrong fact taught. Reward → curriculum → reward, the same closed loop as the exotic pets.
- **Unexpected gifts** (panel suggestion): occasionally, unannounced, the pet has found a small decor item after a session — the reward type research says does *not* undermine intrinsic motivation.
- **Welcome-back moment**: after any gap, the pet is simply delighted and offers one small "I saved this for you" token — zero commentary on the absence.
- Pets evolve visually at 10/25/50 sessions together; the album (§10) keeps their pictures over time. **Rare breed variants** (designer's idea) drop from high-level chests.
- "Pet present in the room" is a server-side **active-pet selection**, not a reading of the room-layout blob (see §12).

### Kindness guardrail — the pet is never sad

Guilt mechanics are explicitly banned in this app. The pet **never** droops, starves, leaves, or gets sad. It sleeps when you're away and is delighted when you return. It only ever gains. Non-negotiable acceptance criterion for any pet spec.

## 9. Exotic pets via prerequisite chains

Designer's idea: rarer pets require preparation you can see — specific rooms, furniture, and completed missions — so the pet is a *goal with visible steps* ("2 of 4 things ready for your snake"), surfaced in the §6 mission pop-up. This maps onto the existing near-achievement pattern, which exists end-to-end today.

Build-on (Claude): theme exotic pets to the **set texts**, so wanting the pet is wanting to revise. The motivation reviewer called this the strongest mechanic in the doc — it converts an external reward into *wanting the curriculum itself*:

| Pet | Requires (sketch) |
|---|---|
| 🐍 Snake | Enclosure (800c) + heat lamp (400c) + a Jekyll & Hyde mission chain (transformation, double natures) |
| 🦉 Owl | Library room + perch + a Macbeth chain ("the owl that shrieked") |
| 🐦‍⬛ Raven | Gothic decor set + a 19th-century-novel / gothic poetry chain |
| 🐯 Tiger | Garden room + endgame poetry-anthology chain — *burning bright*, a Grandmaster-tier goal (the Blake allusion is flavour only: *The Tyger* is not a set anthology poem — his "London" is; its fact card must say so) |

Exotic pets have their own friendship tracks and favourites (the snake favours the heat lamp, naturally). Chains keyed on session-level topic counts are speccable **today**; only chains needing per-turn signals inherit the voice-session capture gap.

**Multi-subject pattern — subject mascots and rare pets** (§2; designer's design): every subject gets **(a) a mascot pet** that represents it, earned by early depth in that subject (sketch: ~10 qualifying sessions), and **(b) rarer pets** behind prerequisite chains, like English's four above. Over time the pet family becomes a quiet record of which subjects the student has gone deep in. Sketch menagerie (designer's entries for French and Spanish):

| Subject | Mascot | Rare pets (chain sketch) |
|---|---|---|
| English | — (first pack; its chains are the four above) | 🐍 snake, 🦉 owl, 🐦‍⬛ raven\*, 🐯 tiger |
| French | 🐓 Gallic rooster, France's beloved (unofficial) national symbol — officially that's Marianne — chain includes **morning sessions** ("roosters announce the start of the day"; mechanically this reuses the existing before-09:00 Morning Star signal, so it is speccable today) | 🐔 Bresse hen — tied to *Les Glorieuses de Bresse*, the real December poultry festival, so it drops from the Christmas event's French track |
| Spanish | 🐎 Spanish horse — the elegant Andalusian breed *or* the wild Galician ponies of *Rapa das Bestas* (two distinct traditions from opposite ends of Spain; pick one lineage) | 🐂 Toro bravo, Spain's national animal |
| History | 🕊️ Messenger pigeon — the decorated war pigeons of both world wars, including the 32 WWII winners of the Dickin Medal (the "animal Victoria Cross", instituted 1943 — WWI's Cher Ami was decorated before it existed), tied to the wars modules | 🐦‍⬛ Tower raven\* ("if the ravens leave the Tower, the kingdom falls") |
| Maths | 🐢 Tortoise (Zeno's paradox — Achilles and the tortoise) | 🐝 Bee (honeycomb hexagons are provably the optimal shape) |
| Science | 🦎 Axolotl (regeneration, biology's superstar) | "Quantum cat" — a breed variant for a base cat (Schrödinger's, naturally) |

\* The raven is deliberately **cross-subject** — reachable through the English gothic chain *or* a History Tower-of-London chain: the pet-shaped version of the cross-subject festivals above.

Designer's timetable confirmed (History, English, Maths, triple science, French, Spanish): the menagerie above covers it in full. Triple science may eventually justify per-science creatures (the axolotl ships first for Biology; Chemistry and Physics candidates are an open slot).

**Presentation rule (kindness)**: pets are always presented as the animals themselves, never as the contests involving them — the toro bravo arrives as Spain's magnificent national animal grazing in your garden; festival culture is carried by the event mission tracks, not by the pet's framing.

## 10. The album (designer's idea)

A gallery of everything that has grown, reached from the §6 menu:

- **Postcards** — every room snapshot you've saved, oldest to newest: the September-to-April story in pictures.
- **Pet pages** — tap a pet to see its pictures over time, "from when you first got them compared to how they are now, so you can see how they have improved and grown as well." (Implementation: renders of past evolution stages, derivable from stage history — no stored photos needed.)
- **Trophy room** — trophies from *important* milestones only, deliberately rare so they stay meaningful (designer's rule): Boss Battle "Exam Ready" trophies (already in the ratified design), 100/200 lifetime study days, Grandmaster, a completed exotic-pet chain. Trophies are display-only prestige — no coin value. The trophy room displays **only earned trophies**: no silhouettes, empty pedestals, or "???" placeholders — a checklist of gaps is a guilt surface, and this room is a celebration, not an audit.
- **Fact cards** (designer's idea, §8) — every fun fact earned from subject-milestone outfits, collected in one place: the wardrobe doubles as a museum of things learned. Shows **only earned cards** — no card backs, empty slots, or collected/total counts (§12).
- **Profile** — a personalised page: favourite topic (derived from most-studied, or chosen), favourite furniture set, chosen pet portrait, key stats (total study time, lifetime days, longest streak).

## 11. Seasonal events and memory crystals (designer's idea)

- **Month-long themed events** (Halloween, Christmas…): festive missions, festive minigames, and event-exclusive furniture and pet accessories. Items are deliberately **not hard to get** within the month — events are "fun while you study… which makes studying feel less like a chore."
- **XP integrity rule**: event *missions* are real study sessions themed festively — they pay XP as normal sessions do. Event *minigames* are pure fun and pay **coins and event items only, never XP**.
- **Memory crystals** (designer's solution to seasonal FOMO): earned from level-ups; spending one **replays a past event in full**, minigames and all, "therefore you won't miss out on any items or minigames." **Kindness floor** (review — level-ups alone dry up at Grandmaster and slow between late levels): any event not completed in its month automatically banks one free replay ~4 weeks later, and after Grandmaster crystals drop from lifetime-days milestones and topic chests instead. With the floor in place, no seasonal item is ever permanently missable — the floor plus crystals, not crystals alone, is what satisfies the §7 recurrence rule.
- **Replay pays honestly for free**: the coin/item ledger's `UNIQUE(source_kind, source_id)` dedupe (§14) *is* the replay rule — a replay pays only sources not yet earned, so partial completions finish honestly and repeat replays are pure fun plus capped minigame coins, never a farmable faucet.
- **Events are cross-subject festivals, not English-owned** (§2; designer's insight): for several subjects the festival *is* syllabus content — the languages GCSE examines customs and festivals directly (Noël, La Navidad, Día de los Muertos, Semana Santa…), and History modules carry seasonal anchors (the Victorians invented the modern Christmas in the same decade Dickens wrote *A Christmas Carol*, so the English and History tracks reinforce each other; a Cold-War winter theme also fits the season). So one event = **one shared season in the home, with a mission track per subject the student takes**. Christmas: the Carol (English), Noël customs (French), La Navidad (Spanish), the Victorian Christmas (History). Halloween: gothic texts (English), the Victorian era (History), Día de los Muertos (Spanish), La Toussaint (French). Every track is real revision wearing the same costume; subjects without a natural link that season simply sit it out — no filler missions.
- **Cadence rule** (review): 3–4 events per season with deliberate quiet months between — permanent festival kills novelty — and no new event opens within ~4 weeks of the April open house; the final stretch belongs to the finale, not a competing theme.
- **Archive**: a menu page of past events and what each one gave you. Framing rule (review): one unified list of "**seasons you can visit**" — never "missed", and no completion percentages or item counts on unvisited events. An unvisited season reads as an invitation, not a gap.
- Build-on (Claude) — **the set texts are seasonal**: December's event can *be* A Christmas Carol (festive missions = Carol revision, Victorian furniture set, a robin visitor), and October's can be gothic month (Jekyll & Hyde / the raven chain). The events then aren't a break *from* revision — they're revision wearing a costume, same principle as the exotic pets.
- **Event calendar** (designer's call): the **first event to build is Christmas / *A Christmas Carol***, then a rolling annual calendar — **New Year** (a fresh-start event; January is also mocks season, and the fresh-start effect is exactly when re-engagement lands best), **Easter** (the big pre-exam revision festival, handing over to the April open house), **Halloween** (gothic month), and more as the template matures. Events that ran before a student joined are reachable via memory crystals — the calendar never strands anyone.
- Cost honesty: events are content-hungry (theme art + minigame build). Recommend **one reusable event template** (mission set + 1–2 tiny minigame mechanics) reskinned per season, not bespoke events.

## 12. Kindness guardrails (consolidated — inherit verbatim as acceptance criteria)

1. The pet is never sad, never leaves, never loses anything (§8).
2. No item, charm, minigame, or bonus ever changes an XP amount (§2, §11, §13).
3. Nothing is ever taken away: items, pets, friendship, rooms, trophies are append-only (§2).
4. No real money touches anything, ever; chests are earned-only (§2, §13).
5. No permanent-loss scarcity: exclusives recur, shop stock returns, missed events replay via memory crystals, "last chance" copy is banned (§7, §11).
6. Treats capped; a session always out-earns a day of treats (§8).
7. Fair-chest rules: pity timer, no dupes, visible odds, no gambling theatre (§13).
8. Welcome-backs are warm and comment-free; consistency income honours a 5-day week and lifetime days, not just unbroken streaks (§4, §8).
9. Postcards are shared by the student's explicit choice only; no in-app social surface (§1).
10. The front-door HUD shows only numbers that grow; the streak flame never renders zeroed, dimmed, or at-risk states there — after a reset the slot shows lifetime days until a new streak reaches 3 (§6).
11. A qualifying session always out-earns a day of minigame play; minigame coins cap per London day (§4, §11).
12. Trophy room, archive, fact cards, and the pet wardrobe display only what has been earned or visited — no silhouettes, empty slots, "???" cards, "missed" labels, or completion counts; unvisited events read as "available to visit" (§10, §11).
13. Pets are presented as the animals themselves, never as the contests involving them; festival culture lives in event mission tracks (§9).

## 13. Chests and the Focus Charm

- **Topic chests** (designer's idea): every 5 qualifying sessions on the same topic → a chest (topics namespaced by subject — the mechanic itself is subject-neutral, §2). Counting is **cumulative-lifetime** (never windowed or reset) so chest progress never fights the planner's rotation rules, and **progress only accrues while the topic is below Mastered** — a chest must never make re-grinding an easy topic the smart move.
- **Level-up chests**: coins per §4; item odds improve with level; rare breeds at high levels. If one settlement crosses multiple levels (badge-XP cascade), **each level crossed pays its own chest**.
- **Focus Charm** (reshaped on review — the original doubled XP, which broke the honest-record principle and replay determinism): a consumable that **doubles the next session's coins** (20/40/60). Earned-only, rare (chests/quests, ≈1/week). **Anti-waste kindness rule**: student-armed before a session (never auto-consumed) and refunded if the session settles at 0 coins.
- **Fair-chest rules**: earned-only, never purchasable; deterministic bad-luck protection (any advertised rare guaranteed within N chests); no duplicate exclusive drops; contents/odds visible; no near-miss or slot-machine reveal animations — the surprise lives in the *presentation* (what the pet drags in), not in manipulated odds.

## 14. Implementation notes (panel-corrected)

- **Coin earns** ride the existing settlement: computed inside pure `decide()` (extend `GamificationDecision` with `coins_awarded`), banked in the same `finalize_session` transaction, stored as an **append-only `coin_txn` ledger** with `UNIQUE (student_id, source_kind, source_id)` + `ON CONFLICT DO NOTHING`; balance = `SUM(amount)` (the ADR-ARCH-030 D2 idiom — a mutable balance column would break `_replay_settlement` determinism and sweep idempotency).
- **Coin spends are a second transactional path** settlement can't see: a purchase transaction that atomically checks balance, debits (negative ledger row), grants the item, and credits any set bonus. Same shape for quest and event rewards.
- **Wire contract**: contract **Revision 3** (Rev-2 is frozen; "no field is invented beyond those docs") must enumerate everything the §6 surfaces need, not just coins: coin balance/awards, the **full badge list** (today the wire carries only recent-5 + near-3), total study time, lifetime days, and the §10 profile fields. Coin values need a ratified single-source module mirroring `gamification/economy.py` before build.
- **Items**: sticky rows like achievements, with a **quantity** column for duplicable furniture/decor.
- **Friendship is not sticky-row state**: a monotonic counter over append-only `friendship_event` rows (session-together, first-treat-of-day with London-day rate check, favourite-item trickle, and outfit-milestone — one per outfit, `UNIQUE(student_id, outfit_id)`, banked at earn time since first-wear is client cosmetic state gameplay never reads), derived by summation.
- **Room layout** is a client-owned JSON blob per `(student_id, room_id)`, last-write-wins on `updated_at`. Gameplay never reads it — "pet present" is the server-side active-pet selection; competence artefacts derive from existing achievement/confidence state.
- **HUD/stats**: level/XP/streak fields are already on the wire. **Correction (review)**: no `engagement_seconds` column exists — engagement is derived from `session_turn` timestamps at settlement and discarded. Total study time = either an aggregate over `session_turn` (per-session `max(ts)−min(ts)`, summed; turns are never deleted, so fully backfillable) or a new `session.engagement_seconds` banked at settlement (the value already sits in `SessionFacts.engagement_seconds`) plus a one-off backfill. Count **qualifying sessions only**, and never ship `last_activity − started_at` as "study time" — it overstates the ratified definition. Lifetime days = distinct London **credit days over qualifying sessions** — exactly the set both the settlement and read paths already compute (`len(credit_days)` from the existing fold; SQL form `(last_activity AT TIME ZONE 'Europe/London')::date`). Lifetime-days milestones slot into the achievement catalog pattern with 0 XP.
- **Album**: postcards are client-rendered images (RepaintBoundary capture + a share plugin such as `share_plus` — the app currently bundles **no share package and no image assets at all**, so even sticker-style art means setting up the Flutter asset pipeline from scratch); pet history renders derive from evolution-stage history; trophies are a display tier over existing achievement rows (earned-only, §10).
- **Events**: event definitions + London-calendar gating; **memory crystals** are their own small append-only ledger (source: level-ups); replay instantiates a past event definition outside its calendar window. Minigames are the genuinely new engineering surface — keep to 1–2 tiny mechanics reskinned per season.
- **Chain progress** reuses the near-achievement DTO — include `description` (the Dart parser requires it). Reusing the machinery means growing the decision context with item-ownership and quest signals, W2Signals-style: precedented, but real work.
- **The Quest entity is scaffolding only** (DDL + Pydantic record; zero read/write code). Slice 2's dominant cost is the full quest lifecycle, and the entity needs reward-identity columns (`coin_reward`, `item_reward_id`).
- **Slice-1 schema** (one alembic revision + the mandated `schema_reference.sql` hand-sync): `coin_txn`, `item(student_id, item_id, quantity, acquired_at, source, price_paid)`, `room_layout(student_id, room_id, layout JSONB, updated_at)`. Item catalog lives in code like the achievement catalog.
- **Rough cost map**: CHEAP — coin earns, room/level gates, HUD stats, chain-progress DTO, contract Rev 3. MODERATE — purchase transaction, inventory/layout endpoints, shop UI, album, layout sync, **the navigation shell** (no tab bar exists today), and **the home-shell restructure** (the current home owns session-list fetch, resume/start guards, auth routing, and pull-to-refresh — the §6 front door relocates all of it, it doesn't add a button). EXPENSIVE — the Flutter room renderer (nothing like it exists in `app/lib/ui/` today), the quest lifecycle, the pet system, events/minigames, and **art assets, which dominate everything**.
- Nothing here touches the ratified XP economy — coins are additive, XP values and bands unchanged.
- **Multi-subject (§2) is a schema-day-one concern, not a later port**: today the `subject` param on GET /api/student-model is required but unused, `ProgressStore` is pinned to `defaultSubject='english'`, and `topic_confidence` is a flat topic→score map. Topic keys, chest counters, chain definitions, and achievement catalogs all need a `subject` dimension from the **first** migration (cheap now, painful later). Whole-student totals (XP, coins, streaks, lifetime days, level) stay unscoped; only mastery/topic surfaces filter by subject. The W2 signal layer (`texts.py`, `catalog_w2.py`) becomes the English instance of a per-subject signal/catalog pack. Prompt management and per-subject RAG artifacts (set texts, study-guide packs) are a **separate workstream, out of scope here** — this design only requires that content packs key on the same subject identifiers that workstream settles on.

## 15. Build order (designer's priority) and pacing

1. **Coins + shop + bedroom** (as a tab first, §6 staging) — the smallest slice that makes hard work visible. **Art is the critical path**: style decision **RESOLVED 20 July 2026** — detailed storybook watercolour, designer-signed-off after Flux style tests on the Spark (dark-academia ornate reserved as a candidate earnable room-makeover set); still needed: one backdrop, ~20–30 coherent sprites. Phase-1 session coins at 15/30/45 to bridge the income gap until step 2.
2. **Furniture sets + exclusive items** — needs quests/daily challenges (FEAT-PO-008) or topic chests as sources; includes the quest lifecycle build.
3. **First pet + friendship** — Level 5 gate, favourites, treats, welcome-back, the never-sad rule.
4. **Room becomes the home screen + album** — the §6 front door, postcards, trophy room, profile.
5. **More rooms + expansions** — Library/Garden/Lounge; expansions as late-season sinks.
6. **Exotic pet chains + breed variants** — endgame content; topic-count chains first.
7. **Seasonal events + memory crystals + archive** — one reusable template; first outing **December *A Christmas Carol*** (designer's call), then the annual calendar per §11.

**Season income model** (5 standard sessions/week; the level curve independently lands Grandmaster ≈ week 30 at this pace): full build ≈ 450–550c/week vs. sets at 1,000–3,000c ⇒ roughly one set per 3–6 weeks, 5–7 sets a season. Retune §4/§7 numbers against this model, not vibes.

## 16. Open questions

- **Coin backfill at launch**: mint coins retroactively from banked XP/achievement history (a mid-season student starts with a shop spree — endowed progress in currency form; *recommended*) or start at zero? Must be deterministic either way.
- **Re-earnable streak coins**: with weekly-consistency and lifetime-days income as the workhorses, once-ever streak coins are simpler (*recommended*); re-earning per run would need a per-run ledger `source_id`.
- **Memory-crystal earn rate**: one per level-up feels right early (14 crystals across a season vs. 3–4 events), but tuning must cover the terminal cases the §11 kindness floor exists for — Grandmaster students and the ~6-week Level-14→15 drought.
- Pet art direction and budget — the binding constraint (§14/§15).
- **Per-subject pack parity**: subject packs should be sized comparably (achievements, chains, sets) so no subject reads as the poor relation. What's the minimum viable pack — one exotic chain + one furniture set + a handful of mastery badges? Who authors packs as subjects are added?
- **Subject surfaces in the UI**: the §6 HUD and room are whole-student; where does per-subject mastery live — tabs on the progress page, shelves on the bookcase, the profile? And when does the deferred subject picker land?
- Should treats/toys do anything beyond friendship/animations long-term, to keep the pet shop section meaningful?
