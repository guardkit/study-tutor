# Conversation Starter: GCSE Study Tutor Access for Lilymay

**Date:** 2026-04-29
**Purpose:** Set up Lilymay's access to the fine-tuned GCSE English study tutor running on the GB10.
**For:** Claude Code session on the GB10

---

## What's Already Deployed

The fine-tuned Gemma 4 26B-A4B GCSE English tutor is **live and serving** on the GB10 via llama-swap:

| Component | Details |
|---|---|
| **Model** | `gemma-4-26b-a4b-it.Q4_K_M.gguf` — fine-tuned on GCSE English training data via Unsloth QLoRA |
| **Endpoint** | `http://localhost:9000/v1` (llama-swap, OpenAI-compatible API) |
| **Model aliases** | `gemma4-tutor`, `study-tutor`, `gcse-tutor` |
| **System prompt** | Stored at `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` (extracted from the Ollama Modelfile) |
| **Serving flags** | `--temp 0.7 --top-p 0.9 --ctx-size 32768 --jinja --chat-template-file /opt/llama-swap/config/gemma4-tutor.jinja` |
| **Template leak fix** | Custom Jinja template deployed to strip `<|channel>thought<channel|>` markers. Will be retired after next fine-tune with `--chat-template gemma-4`. |
| **Tailscale hostname** | `promaxgb10-41b1` (accessible from any device on the Tailscale network) |

The API is OpenAI-compatible. Quick verification:
```bash
curl -s http://localhost:9000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "gemma4-tutor",
        "max_tokens": 512,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": "<contents of /opt/llama-swap/models/gemma4-tutor/system-prompt.txt>"},
            {"role": "user", "content": "How do I improve my answer on Paper 1 Question 5?"}
        ]
    }'
```

---

## Who is Lilymay?

- Year 10 student at Robert Blake School (United Learning curriculum)
- Studying AQA specification across all subjects
- Currently studying: English Language (8700), English Literature (8702), Maths, French (8652), Spanish (8692), History, Triple Science (Biology, Chemistry, Physics)
- Has been struggling with homework and revision
- Age 14-15 — all interactions must be age-appropriate, encouraging, and supportive
- Needs a patient, Socratic tutor — guides her to answers rather than giving them directly

---

## What Lilymay Needs

### A simple chat interface to the GCSE English tutor

She needs to:
1. Open a web page on her laptop/phone/tablet
2. Type a question about her English homework or revision
3. Get a helpful, encouraging, Socratic response
4. Have multi-turn conversations (tutor remembers context within a session)

She does **not** need to:
- Know about llama-swap, APIs, models, or any infrastructure
- Configure anything
- Install anything beyond a web browser

### The system prompt must be baked in

The fine-tuned model was trained with a specific system prompt that shapes its Socratic behaviour. This must be sent with every request automatically — Lilymay should never see it. Read it from `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt`.

---

## Recommended Approach: Open WebUI

Open WebUI is an open-source ChatGPT-style interface that connects to OpenAI-compatible APIs. Lilymay has used it before.

### Setup steps

1. **Install Open WebUI on the GB10** (Docker preferred for isolation):
```bash
docker run -d \
    --name open-webui \
    --network host \
    -v open-webui-data:/app/backend/data \
    -e OPENAI_API_BASE_URL=http://localhost:9000/v1 \
    -e OPENAI_API_KEY=not-needed \
    --restart unless-stopped \
    ghcr.io/open-webui/open-webui:main
```

2. **Access the admin panel** at `http://promaxgb10-41b1:8080` (or whatever port Open WebUI binds to). Create an admin account on first visit.

3. **Create a "GCSE English Tutor" model preset:**
   - Go to Workspace → Models → Create Model
   - Name: `GCSE English Tutor`
   - Base model: select the llama-swap connection, model `gemma4-tutor`
   - System prompt: paste the contents of `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt`
   - Temperature: 0.7
   - Description: "Your personal GCSE English tutor — ask me anything about English Language or Literature!"
   - Set an encouraging avatar/icon

4. **Create a user account for Lilymay:**
   - Username: `lilymay`
   - Set a simple password she'll remember
   - Default model: GCSE English Tutor

5. **Test the full round-trip:**
   - Log in as Lilymay
   - Start a new chat
   - Type: "Help me with my Macbeth essay"
   - Verify: encouraging, Socratic response with AQA mark scheme references
   - Verify: no template tokens (`<|channel>`, `<think>`) visible

6. **Bookmark for Lilymay's devices:**
   - On her laptop/phone/tablet, open `http://promaxgb10-41b1:8080` in the browser
   - All devices must be on the Tailscale network (install Tailscale app, Rich approves the device)
   - Alternatively, if devices are on the same home LAN, use the GB10's local IP

---

## Stretch Goal: Multi-Subject Presets

The fine-tuned model is **English-only**. For other subjects, the base Gemma 4 model can still provide useful tutoring with a good subject-specific system prompt. Create additional model presets in Open WebUI:

| Subject | AQA Spec | System Prompt Focus |
|---|---|---|
| Maths | AQA | Step-by-step problem solving. Show working. Guide through method, don't just give answers. |
| French | AQA 8652 | Vocabulary, grammar, reading comprehension, translation practice. Encourage use of target language. |
| Spanish | AQA 8692 | Same approach as French but for Spanish. |
| History | AQA | Source analysis, chronological understanding, historical interpretations. Reference key events and themes from the specification. |
| Biology | AQA Triple | Scientific method, key concepts, required practicals. Explain with diagrams where helpful. |
| Chemistry | AQA Triple | Atomic structure, bonding, reactions. Balance equations step by step. |
| Physics | AQA Triple | Forces, energy, waves, electricity. Guide through calculations with units. |

Each preset uses the same `gemma4-tutor` model but with a different system prompt. The English tutor will be the best quality (fine-tuned); the others will be decent but not specialist (base model + good prompt).

**Note:** French (8652) and Spanish (8692) are new AQA specs with first exams summer 2027. Only specimen papers exist — fine-tuning for these subjects will need the specimen papers as RAG source material.

---

## Access and Safety

### Network
- GB10 is on Tailscale — all devices accessing the tutor need Tailscale installed
- Rich approves new devices joining the Tailscale network
- No external internet exposure — the tutor is local-only

### Privacy
- All conversations stay on the GB10 — nothing leaves the house
- No cloud APIs involved in inference
- Open WebUI stores conversation history locally on the GB10
- Lilymay's study data is hers — nobody else can see it (unless Rich checks via admin)

### Content safety
- The fine-tuned model was trained to be encouraging, patient, and age-appropriate
- The system prompt reinforces this for every interaction
- Open WebUI supports content filtering if needed

---

## Files on the GB10

| Path | What |
|---|---|
| `/opt/llama-swap/config/config.yaml` | llama-swap config — tutor model definition |
| `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` | The trained system prompt |
| `/opt/llama-swap/models/gemma4-tutor/Modelfile` | Original Ollama Modelfile (reference) |
| `/opt/llama-swap/models/gemma4-tutor/gemma-4-26b-a4b-it.Q4_K_M.gguf` | Fine-tuned model weights |

---

## Success Criteria

1. Lilymay opens `http://promaxgb10-41b1:8080` on her device and sees a clean chat interface
2. She selects "GCSE English Tutor" and types "Help me with my Macbeth essay"
3. The tutor responds with encouraging, Socratic guidance referencing AQA mark scheme criteria
4. Multi-turn conversation works — the tutor remembers what she said earlier
5. No template tokens (`<|channel>`, `<think>`) visible in any response
6. The interface feels like talking to a helpful teacher, not using a technical tool

---

*Prepared: 2026-04-29*
*Cross-references: RESULTS-v3-production-deployment.md, RUNBOOK-fix-tutor-template-leak.md, GCSE_English_AI_Tutor_Proposal.docx*
