# Licensing and Distribution

This document records what this repository covers, what it does not cover,
and what stays private by design. It is the single reference for any
reviewer (Kaggle, judges, contributors, downstream users) asking "can I use
this, and under what terms?".

The detailed analysis behind these decisions is in
[copyright-training-data-analysis.md](research/ideas/copyright-training-data-analysis.md).
This file is the operational summary.

---

## 1. Repository code

All original source code, configuration, and documentation in this
repository is released under the **MIT License** (see
[LICENSE](../LICENSE) at the repo root).

This covers:

- Python package `study_tutor/` and its submodules (CLI, LLM client, MCP
  adapter, session, roles).
- `scripts/` (bash wrapper for Claude Desktop, etc.).
- `tests/`.
- `domains/gcse-english/GOAL.md`, `docs/gamification/design.md`, the
  `roles/tutor/` configuration, and every other markdown file in this
  repository unless explicitly noted otherwise.
- `pyproject.toml`, `AGENTS.md`, `.env.example`, `.mcp.json`, `.gitignore`,
  `README.md`.

> **Note on the planned licence.** The Phase 0 build plan proposed
> Apache 2.0 for this repo; the LICENSE that actually landed on
> 12 April 2026 is MIT. Both are permissive, OSI-approved licences
> compatible with the Gemma 4 base model's Apache 2.0 terms. If the
> Kaggle hackathon rules specify Apache 2.0 for submissions (to be
> confirmed behind the Kaggle login wall), this file and the LICENSE
> will be updated together.

---

## 2. Gemma 4 base model

The Gemma 4 26B-A4B base model (MoE, ~27B total / ~4B active;
`unsloth/gemma-4-26b-a4b-it`), published by Google DeepMind, is
distributed under **Google's Gemma Terms of Use** (an Apache-2.0-style
licence with a use-policy addendum). *(Corrected 2026-08-01: this file
previously said "31B Dense" — stale and wrong per the 2026-07-06 AWS
hosting research §1; the fine-tune has always been the 26B-A4B MoE.)*
This project does not redistribute the Gemma base weights — they are
pulled from the official registries (Hugging Face, Ollama, AWS Bedrock)
at runtime by the operator.

Operators are responsible for accepting Google's Gemma terms in the
registry of their choice before running the tutor.

- Gemma terms: https://ai.google.dev/gemma/terms
- Use policy: https://ai.google.dev/gemma/prohibited_use_policy

---

## 3. Fine-tuned adapter and merged weights — distribution status (corrected 2026-08-01)

The fine-tuned weights are **not distributed in this repository**, but —
correcting the earlier "NOT distributed" claim of this section — they
**were deliberately uploaded to the Hugging Face Hub**: the merged 16-bit
weights and the GGUF export live at
`RichWoollcott/gcse-tutor-gemma4-26b-moe` (+ `-GGUF`), linked from the
hackathon submission writeup §11 and verified on the Hub in the
2026-07-06 AWS hosting research §1. The upload was a **requirement of the
Kaggle "Gemma 4 Good" hackathon entry** — a conscious decision, not a
leak (Rich, recorded 2026-08-01; mission dated note 4). This file
previously contradicted that fact; the record now stands as fact +
reason, per [ADR-ARCH-031 D4](architecture/decisions/ADR-ARCH-031-pilot-uploads-copyright-posture.md).
(The FEAT-PO-004 Bedrock Custom Model Import destination this section
once named is dead — CMI cannot import Gemma at all, per the 2026-07-06
research §2.)

Context that still holds:

- The fine-tune was trained on synthetic data generated with reference to
  commercially purchased, DRM-free study guides (see §5). The training
  output is original synthetic content; the 2026-04-12 analysis §7.2
  rated public weight distribution "Medium" risk with the mitigation that
  weights are numerical behaviour, several transformative steps from any
  source text. That assessment stands; the hackathon entry was the
  decision to accept it.
- The adapter (~600 MB) and merged 16-bit weights (~49 GB safetensors)
  exceed what belongs in a git repository regardless of licensing
  posture — the Hub, not this repo, is where they live.
- Any **further** distribution decision is blocked on resolving the
  base-model licence identity conflict (Apache 2.0 in the writeup vs
  Gemma Terms of Use here — AWS research §1/§6c), tracked in
  ADR-ARCH-031 D4.2.

Reproducing the fine-tune requires the separate
[`agentic-dataset-factory`](https://github.com/appmilla/agentic-dataset-factory)
pipeline, an operator-acquired study-guide corpus (see §5), and GB10-scale
compute. The pipeline is open; the weights live on the Hub (above), not
in this repository.

---

## 4. GGUF / Ollama deployment artefacts — distribution status (corrected 2026-08-01)

The `gemma-4-26b-a4b-it.Q4_K_M.gguf` quantised export used for local
inference is a derivative of the fine-tuned weights described in §3 and
shares their status: not in this repository, but published to the Hub in
the `-GGUF` companion repo as part of the same hackathon upload (the
BF16 GGUF there is unusable — shard 1 missing, per the AWS research §1).
*(The "equivalent 31B quantised exports" this section previously named
never existed — the 31B identity was stale, see §2.)*

The `Modelfile` that wraps them (with the GCSE English system prompt and
sampling parameters) is considered configuration, not model weight, and
may be published in this repository under §1 terms when the Phase 1
deployment tooling lands.

---

## 5. Third-party source material — NOT distributed

The study guides and curriculum materials used to seed the RAG knowledge
layer and generate synthetic training data are **not distributed in this
repository**. They are retained only on the developer's and operator's
own machines, per the purchase/licence terms under which they were
acquired.

| Source | Status | Notes |
|--------|--------|-------|
| Mr Bruff GCSE English guides (mrbruff.com) | Private | Purchased DRM-free PDFs. No AI prohibition in terms of sale, but no AI licence either — treated conservatively and never published. |
| CGP / York Notes / Pearson Revise / Collins | Private | Operator-acquired; same treatment as above. |
| AQA past papers, mark schemes, examiner reports | **Excluded from the pipeline entirely** | AQA's Copyright & Intellectual Property Policy explicitly prohibits use of AQA materials "in any manner or for any purposes in connection with the training of Artificial Intelligence powered tools or technologies" ([source](https://www.aqa.org.uk/about-us/who-we-are/our-standards/copyright-and-intellectual-property-policy)). These materials are not used as RAG context, not used as training data, and not published. |
| AQA specification documents (8700 / 8702 curriculum structure) | Referenced only | Factual curriculum information — paper structure, AO definitions. Used the same way any textbook publisher references a specification. Not ingested into RAG or training data. |

The `domains/gcse-english/sources/` directory in this repository is a
**bring-your-own-sources placeholder**. The repository's `.gitignore`
excludes every PDF placed under it so that operator-acquired material
stays on the operator's machine. See
[domains/gcse-english/sources/README.md](../domains/gcse-english/sources/README.md)
for acquisition guidance.

---

## 6. Synthetic training data (`train.jsonl`) — NOT distributed

The synthetic tutoring conversations generated by the Player-Coach
adversarial loop (see the `agentic-dataset-factory` repository for the
pipeline) and written to `train.jsonl` are original synthetic content, but
because they were generated with reference to §5 source material, the
training data file itself is not distributed in this repository.

The schema and generation pipeline are open; the data is not.

---

## 7. Runtime dependencies

All third-party Python packages are pulled from PyPI at install time and
retain their own licences. A non-exhaustive summary of the key
dependencies:

| Dependency | Licence | Role |
|------------|---------|------|
| `mcp` (Model Context Protocol SDK) | MIT | MCP server runtime |
| `click` | BSD-3-Clause | CLI framework |
| `pydantic` | MIT | Schema validation |
| `langchain-*` (openai / anthropic / google-genai / aws / ollama) | MIT | Provider abstraction |
| `ollama` (Python client) | MIT | Local/GB10 inference path |
| `boto3` | Apache-2.0 | AWS Bedrock path (FEAT-PO-004) |
| `graphiti-core` (Phase 1 only) | Apache-2.0 | Knowledge graph (not Phase 0) |

Operators are responsible for reviewing the installed tree (`.venv/bin/pip
show <name>`) if they need exhaustive licence provenance.

---

## 8. What a downstream user can and cannot do

**Can:**

- Fork this repository and use every file in it under MIT terms.
- Adapt the `roles/tutor/` configuration and the `GOAL.md` template for
  other subjects or specifications.
- Run the tutor against their own fine-tune, against the stock Gemma 4
  26B-A4B base model, or against any other LLM provider supported by the
  `llm/client.py` factory.
- Acquire their own study-guide corpus, run the
  `agentic-dataset-factory` pipeline, produce their own `train.jsonl`,
  and fine-tune their own model.

**Cannot:**

- Obtain the fine-tuned weights, LoRA adapter, GGUF exports, or
  `train.jsonl` from this repository — they are not here. (The merged
  weights and Q4_K_M GGUF are on the Hugging Face Hub under Rich's
  account — see §3 — subject to the Hub repo's own terms, not this
  repository's MIT licence.)
- Expect AQA-branded assessment content anywhere in the pipeline.
- Assume that a derivative using AQA materials as training data would be
  acceptable under AQA's policy — it would not, and AQA's policy is a
  constraint on the downstream user just as it is on this project.

---

## 9. Honest framing

The copyright environment for education AI in the UK (and globally) is
unsettled. The Gemma 4 base model this project builds on was itself
trained on a corpus that includes copyrighted works. A solo developer
building a tutor for one student is navigating constraints that the
frontier model providers have not themselves resolved.

This project's posture is conservative and transparent: the *pipeline* is
open, the *data* is private, the fine-tuned *weights* are published on
the Hub as a recorded hackathon-entry decision (§3), and the
*assessment-board-prohibited content* (AQA) is excluded from the
pipeline entirely. The pilot-uploads posture (per-account private
retrieval of user-owned scans) is governed by
[ADR-ARCH-031](architecture/decisions/ADR-ARCH-031-pilot-uploads-copyright-posture.md).
If the posture needs to change again, this document is updated in
lockstep with the change.

---

*Licensing summary: 20 April 2026. Amended 2026-08-01 (Lane 4): recorded the deliberate Hugging Face weights upload (Kaggle Gemma 4 Good entry requirement) and corrected the stale "31B Dense" model identity to the real fine-tuned Gemma 4 26B-A4B. Revisit when the base-model licence identity conflict (ADR-ARCH-031 D4.2) is resolved or when the Lane 3 upload surface lands.*
