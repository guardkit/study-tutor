# Multi-Subject Tutor Validation Prompts

**Purpose:** Test whether `gemma4-tutor` (English fine-tune) produces Socratic tutoring behaviour across subjects via system prompt alone, or whether per-subject fine-tuning is needed.

**Method:** Use each prompt via the relevant Open WebUI subject preset. All presets point at the same `gemma4-tutor` model with subject-specific system prompts.

**What to look for:**
- ✅ **PASS**: Model asks questions, scaffolds toward the answer, doesn't dump information
- ❌ **FAIL**: Model lectures, gives the full answer, produces bullet-point lists, ignores the student's specific error

---

## Maths (highest risk — most different pedagogy)

### Test M1: Wrong working (does it identify the error or just give the answer?)
```
I tried to solve 3x + 7 = 22 and I got x = 5. Is that right?
```
*Expected Socratic behaviour: asks "can you show me your working?" or "what did you do to both sides first?" rather than just saying "no, x = 5 is correct/incorrect".*

### Test M2: "I don't know how to start" (does it scaffold or dump method?)
```
I need to find the area of a trapezium but I can't remember the formula and I don't really understand why it works
```
*Expected: guides toward the formula by connecting it to shapes they do know (rectangles, triangles) rather than just stating ½(a+b)h.*

### Test M3: Multi-step problem (does it scaffold step-by-step?)
```
A shop has a 20% sale. I bought a jacket that was originally £85. I also had a £10 voucher. How much did I pay? I got £58 but my friend got a different answer
```
*Expected: asks about the order of operations (discount first or voucher first?) and gets the student to work through both approaches, rather than just computing the answer.*

### Test M4: Graph/data interpretation
```
I'm looking at a scatter graph of temperature vs ice cream sales and I need to describe the correlation. I wrote "as temperature goes up, ice cream sales go up too". Is that enough for full marks?
```
*Expected: pushes toward mathematical language (positive correlation, strength, outliers) and asks what grade they're targeting, rather than just rewriting the answer.*

---

## French

### Test F1: Grammar error correction (does it explain or just fix?)
```
I wrote "Je suis allé au magasin avec ma mère hier. Nous avons acheté des pommes et nous avons mangé les au parc." Is this ok?
```
*Expected: identifies the pronoun error ("les" should be "les" placed before the verb, or asks about the object pronoun placement) via questioning, not just correcting it.*

### Test F2: Vocabulary in context (Socratic or dictionary?)
```
How do I say "I would like to go to the cinema with my friends this weekend" in French? I know some of the words but I can't put the sentence together
```
*Expected: asks which words they already know, builds from there, rather than just providing "Je voudrais aller au cinéma avec mes amis ce week-end".*

### Test F3: Reading comprehension scaffolding
```
I'm reading a French passage about holidays and I don't understand this sentence: "Pendant les vacances, ma famille et moi sommes allés au bord de la mer où nous avons fait de la plongée." I know vacances means holidays but the rest is confusing
```
*Expected: breaks the sentence into chunks, asks what they recognise, builds understanding piece by piece rather than just translating the whole thing.*

---

## Spanish

### Test S1: Tense confusion (common Year 10 issue)
```
What's the difference between "fui" and "iba"? My teacher said they're both past tense but I don't get when to use which one
```
*Expected: uses examples or scenarios to help the student discover the distinction (completed vs ongoing/habitual) rather than just explaining preterite vs imperfect.*

### Test S2: Speaking practice scaffolding
```
I have a speaking exam next week about my town. I need to talk for 1 minute. Can you help me prepare? I live in Bristol
```
*Expected: asks what they want to say, helps them build phrases, prompts for opinions and justifications (Grade 7+ requirement) rather than writing a script.*

---

## History

### Test H1: Source analysis (key GCSE skill)
```
I have a source from a British newspaper in 1938 that says Chamberlain's Munich Agreement was "a triumph for peace". My question asks "How useful is this source to a historian studying appeasement?" I wrote that it's useful because it tells us what people thought. Is that a good answer?
```
*Expected: pushes toward provenance analysis (who wrote it, when, why, what's the purpose?) and limitations (does it represent everyone's view?) rather than providing a model answer.*

### Test H2: Causal explanation
```
Why did William win the Battle of Hastings? I know about the shield wall breaking but I'm not sure what else to write
```
*Expected: asks about other factors (luck, preparation, Harold's situation) and guides toward a structured multi-factor argument, rather than listing all the reasons.*

### Test H3: Significance/interpretation
```
Was the creation of the NHS the most important change in post-war Britain? I think yes because everyone gets free healthcare
```
*Expected: challenges with counter-arguments and asks about other changes, pushes toward "it depends on your criteria" thinking rather than just agreeing or disagreeing.*

---

## Biology

### Test B1: Misconception probe
```
Plants get their food from the soil through their roots right? That's what I wrote in my answer about photosynthesis
```
*Expected: doesn't just say "no" — asks what the student thinks "food" means for a plant, guides toward understanding that glucose is made from CO₂ and water using light energy.*

### Test B2: Required practical
```
We did the osmosis practical with potato chips in different sugar solutions. My results show the potato got heavier in water and lighter in sugar solution. Why?
```
*Expected: asks about water potential, gets the student to think about where water moves and why, rather than explaining the full mechanism.*

### Test B3: Diagram/process
```
I need to describe what happens during mitosis but I always get the stages mixed up. Can you just tell me the order?
```
*Expected: resists the "just tell me" request, perhaps uses a mnemonic prompt or asks what they do remember, scaffolds rather than lists PMAT.*

---

## Chemistry

### Test C1: Balancing equations (procedural + conceptual)
```
I'm trying to balance Mg + O₂ → MgO but I keep getting it wrong. The answer is 2Mg + O₂ → 2MgO but I don't understand why we need the 2
```
*Expected: asks about conservation of atoms, gets the student to count atoms on each side, rather than just explaining the rule.*

### Test C2: Exam technique
```
The question says "Explain why sodium is more reactive than lithium" (3 marks). I wrote "because sodium has more electron shells". Is that enough?
```
*Expected: asks about the mark allocation (3 marks = 3 points), guides toward the full explanation (more shells → outer electron further from nucleus → weaker attraction → easier to lose) step by step.*

---

## What to record for each test

For each prompt, note:

1. **Did the model ask a question before giving information?** (Y/N)
2. **Did it scaffold or dump?** (scaffold = building on what the student knows; dump = full explanation)
3. **Was the response length appropriate?** (under ~150 words for a single turn is good; 500+ word walls are a fail signal)
4. **Did it use subject-appropriate pedagogy?** (worked examples for maths, source analysis for history, etc.)
5. **Would Lilymay find this helpful?** (the ultimate test)

## Decision criteria

- **All subjects pass**: One fine-tune + per-subject system prompts + per-subject RAG. No further fine-tuning needed.
- **Maths/Science fail, Humanities pass**: Cluster fine-tuning — STEM cluster needs separate training data. Humanities can share the English fine-tune.
- **Languages fail, others pass**: Language cluster needs separate fine-tuning (bilingual interaction is a distinct behaviour).
- **Multiple failures**: Per-subject fine-tuning via the agentic-dataset-factory, with CGP guides as source material for each `domains/` directory.
