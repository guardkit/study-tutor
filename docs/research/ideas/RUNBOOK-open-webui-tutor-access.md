# Runbook: Open WebUI — GCSE Study Tutor Access for Lilymay

**Status:** Not yet executed
**Purpose:** Deploy Open WebUI on the GB10 to give Lilymay a ChatGPT-style interface to the fine-tuned GCSE English tutor, with stretch-goal presets for other subjects.
**Machine:** Dell DGX Spark GB10 (`promaxgb10-41b1`), 128 GB unified memory
**Predecessor:** `RUNBOOK-fix-tutor-template-leak.md` (template leak resolved), `RESULTS-v3-production-deployment.md` (llama-swap production config)
**Conversation starter:** `study-tutor/docs/research/ideas/study-tutor-access-conversation-starter.md`
**Expected duration:** ~30 minutes (Docker pull + config + smoke test)

---

## Context

The fine-tuned Gemma 4 26B-A4B GCSE English tutor is live and serving on the GB10 via llama-swap at `http://localhost:9000/v1`. The template-token leak (`<|channel>thought<channel|>`) has been fixed via a custom Jinja template. What's missing is the **last mile** — a clean web interface so Lilymay can just open a browser, pick "GCSE English Tutor" from a dropdown, and start chatting.

Open WebUI is the recommended path. Lilymay has used it before. It's a single Docker container, provides conversation history, mobile support, and a ChatGPT-style interface.

### What this runbook does

1. Deploys Open WebUI as a Docker container on the GB10
2. Reads the trained system prompt from disk and bakes it into a model preset
3. Creates Lilymay's user account with the English Tutor as her default model
4. Smoke-tests the full round-trip (login → chat → Socratic response → no template leaks)
5. (Stretch) Creates multi-subject presets for other GCSE subjects using the base model + subject-specific system prompts

### What this runbook does NOT do

- **Tailscale device approval** — Rich must manually approve Lilymay's device(s) on the Tailscale admin console so she can reach `promaxgb10-41b1:8080` from her laptop/phone/tablet.

---

## Phase 0: Pre-flight

### 0.1 Confirm llama-swap is serving the tutor

```bash
echo "=== Pre-flight: checking llama-swap tutor endpoint ==="
RESPONSE=$(curl -s --max-time 10 http://localhost:9000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "gemma4-tutor",
        "max_tokens": 64,
        "temperature": 0.7,
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }' 2>&1)

if echo "$RESPONSE" | python3 -c "import sys, json; json.load(sys.stdin)['choices'][0]['message']['content']" >/dev/null 2>&1; then
    echo "PASS: llama-swap is serving gemma4-tutor"
else
    echo "FAIL: llama-swap not responding for gemma4-tutor"
    echo "Response: $RESPONSE"
    echo ""
    echo "Check: is llama-swap running? (systemctl --user status llama-swap)"
    echo "Check: does config.yaml have gemma4-tutor? (grep gemma4-tutor /opt/llama-swap/config/config.yaml)"
    exit 1
fi
```

### 0.2 Confirm the system prompt file exists

```bash
SYSTEM_PROMPT_FILE="/opt/llama-swap/models/gemma4-tutor/system-prompt.txt"
if [ -f "$SYSTEM_PROMPT_FILE" ]; then
    echo "PASS: System prompt found at $SYSTEM_PROMPT_FILE"
    echo "Length: $(wc -c < "$SYSTEM_PROMPT_FILE") bytes, $(wc -l < "$SYSTEM_PROMPT_FILE") lines"
else
    echo "FAIL: System prompt not found at $SYSTEM_PROMPT_FILE"
    echo ""
    echo "This file should have been extracted from the Ollama Modelfile during v3 deployment."
    echo "Check the Modelfile at /opt/llama-swap/models/gemma4-tutor/Modelfile and extract the SYSTEM block."
    exit 1
fi
```

### 0.3 Confirm port 8080 is available

```bash
if ss -tlnp | grep -q ':8080 '; then
    echo "WARNING: Port 8080 is already in use:"
    ss -tlnp | grep ':8080 '
    echo ""
    echo "If this is an old Open WebUI instance, stop it first: docker stop open-webui && docker rm open-webui"
    echo "If it's something else, choose a different port in Phase 1 (add -e PORT=8081 to docker run)."
else
    echo "PASS: Port 8080 is available"
fi
```

### 0.4 Confirm Docker is available

```bash
if command -v docker &>/dev/null; then
    echo "PASS: Docker is available ($(docker --version))"
else
    echo "FAIL: Docker not found. Install Docker first."
    exit 1
fi
```

---

## Phase 1: Deploy Open WebUI

### 1.1 Pull and run the container

> ⚠️ **`--network host`** is used so Open WebUI can reach llama-swap on localhost:9000. This means Open WebUI binds directly to the host's port 8080. This is fine for a Tailscale-only machine — there's no external internet exposure.

```bash
echo "=== Deploying Open WebUI ==="
docker run -d \
    --name open-webui \
    --network host \
    -v open-webui-data:/app/backend/data \
    -e OPENAI_API_BASE_URL=http://localhost:9000/v1 \
    -e OPENAI_API_KEY=not-needed \
    --restart unless-stopped \
    ghcr.io/open-webui/open-webui:main

echo "Waiting for Open WebUI to start..."
for i in $(seq 1 30); do
    if curl -s --max-time 3 http://localhost:8080/api/health 2>/dev/null | grep -q "true\|ok\|healthy"; then
        echo "  attempt $i: healthy"
        break
    fi
    echo "  attempt $i: not ready yet"
    sleep 5
done

# Final check
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 2>/dev/null)
if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 400 ]; then
    echo "PASS: Open WebUI is running on port 8080 (HTTP $HTTP_CODE)"
else
    echo "FAIL: Open WebUI not responding (HTTP $HTTP_CODE)"
    echo "Check logs: docker logs open-webui --tail 50"
    exit 1
fi
```

### 1.2 Create admin account

> ⚠️ **First-visit registration.** Open WebUI creates an admin account from the first user to register. This step uses the API to create the admin account programmatically. If the web UI has already been visited and an admin account exists, this will fail — skip to Phase 2.

```bash
echo "=== Creating admin account ==="

# Open WebUI's first-user signup endpoint
ADMIN_RESPONSE=$(curl -s http://localhost:8080/api/v1/auths/signup \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Rich",
        "email": "rich@appmilla.com",
        "password": "CHANGE_ME_ON_FIRST_LOGIN"
    }')

if echo "$ADMIN_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('token',''))" 2>/dev/null | grep -q '^eyJ'; then
    echo "PASS: Admin account created (rich@appmilla.com)"
    # Extract the JWT for subsequent API calls
    ADMIN_TOKEN=$(echo "$ADMIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
    echo "Admin JWT saved for subsequent steps."
else
    echo "Admin signup returned unexpected response — may already exist."
    echo "Response: $ADMIN_RESPONSE"
    echo ""
    echo "If admin account already exists, log in via the web UI and grab a JWT from"
    echo "Settings → Account → API Keys, then set ADMIN_TOKEN manually:"
    echo '  export ADMIN_TOKEN="your-jwt-here"'
fi
```

---

## Phase 2: Create the GCSE English Tutor preset

This is the critical step. The fine-tuned model was trained with a specific system prompt that shapes its Socratic behaviour. Baking this into the Open WebUI model preset means Lilymay just picks "GCSE English Tutor" from the dropdown — the behaviour is automatic.

### 2.1 Read the system prompt

```bash
echo "=== Reading system prompt ==="
SYSTEM_PROMPT=$(cat /opt/llama-swap/models/gemma4-tutor/system-prompt.txt)
echo "System prompt loaded ($(echo "$SYSTEM_PROMPT" | wc -c) bytes)"
echo ""
echo "First 200 chars:"
echo "${SYSTEM_PROMPT:0:200}"
```

### 2.2 Discover the available model ID

Open WebUI needs to know the exact model ID string that llama-swap exposes. Query the models endpoint to find it.

```bash
echo "=== Discovering model IDs from llama-swap ==="
curl -s http://localhost:9000/v1/models | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('data', []):
    mid = m.get('id', '')
    print(f'  {mid}')
    if 'tutor' in mid.lower() or 'gemma' in mid.lower():
        print(f'    ^^^ this is the tutor model')
"
```

> ⚠️ **Model ID mapping.** llama-swap exposes models by alias (e.g. `gemma4-tutor`, `study-tutor`, `gcse-tutor`). The preset's base model must match one of these exactly. Use `gemma4-tutor` as the canonical alias.

### 2.3 Create the model preset via API

```bash
echo "=== Creating GCSE English Tutor model preset ==="

# Read the system prompt into a Python-safe variable and create the preset
python3 - "$ADMIN_TOKEN" <<'PY'
import sys, json, urllib.request, pathlib

token = sys.argv[1]

# Read system prompt from file
system_prompt = pathlib.Path("/opt/llama-swap/models/gemma4-tutor/system-prompt.txt").read_text().strip()

payload = {
    "id": "gcse-english-tutor",
    "name": "GCSE English Tutor",
    "meta": {
        "description": "Your personal GCSE English tutor — ask me anything about English Language or Literature! I'll guide you to discover answers using the Socratic method.",
        "profile_image_url": ""
    },
    "base_model_id": "gemma4-tutor",
    "params": {
        "system": system_prompt,
        "temperature": 0.7,
        "top_p": 0.9
    }
}

req = urllib.request.Request(
    "http://localhost:8080/api/v1/models/create",
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"PASS: Model preset created — '{result.get('name', 'unknown')}'")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body}")
    print("")
    if "already exists" in body.lower() or e.code == 409:
        print("Preset may already exist. Update it via the admin panel or delete and re-create.")
    else:
        print("Check the Open WebUI API docs for the correct endpoint/payload format.")
        print("The API may have changed — fall back to creating the preset manually via the web UI:")
        print("  Workspace → Models → Create Model")
        print(f"  Name: GCSE English Tutor")
        print(f"  Base model: gemma4-tutor")
        print(f"  System prompt: <paste from /opt/llama-swap/models/gemma4-tutor/system-prompt.txt>")
        print(f"  Temperature: 0.7")
    sys.exit(1)
PY
```

> ⚠️ **API instability.** Open WebUI's API is not officially stable — endpoints and payload shapes change between versions. If the `POST /api/v1/models/create` call fails, fall back to creating the preset manually through the admin web UI at `http://localhost:8080`. The steps are: Workspace → Models → Create Model → fill in name, base model, system prompt, temperature. The conversation starter has the full manual steps.

---

## Phase 3: Create Lilymay's user account

### 3.1 Create the account

```bash
echo "=== Creating Lilymay's user account ==="

# Generate a simple memorable password
# Rich should share this with Lilymay directly
LILYMAY_PASSWORD="Macbeth2026!"

LILYMAY_RESPONSE=$(curl -s http://localhost:8080/api/v1/auths/add \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "{
        \"name\": \"Lilymay\",
        \"email\": \"lilymay@local\",
        \"password\": \"$LILYMAY_PASSWORD\",
        \"role\": \"user\"
    }")

if echo "$LILYMAY_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); assert d.get('id') or d.get('email')" 2>/dev/null; then
    echo "PASS: User account created for Lilymay (lilymay@local)"
    echo ""
    echo "=== CREDENTIALS FOR LILYMAY ==="
    echo "URL:      http://promaxgb10-41b1:8080"
    echo "Email:    lilymay@local"
    echo "Password: $LILYMAY_PASSWORD"
    echo "==============================="
    echo ""
    echo "⚠️  Share these with Lilymay directly. Change the password if needed via the admin panel."
else
    echo "User creation returned unexpected response:"
    echo "$LILYMAY_RESPONSE"
    echo ""
    echo "Fall back to manual creation via admin panel:"
    echo "  Admin Panel → Users → Add User"
    echo "  Name: Lilymay, Email: lilymay@local, Role: User"
fi
```

### 3.2 Set Lilymay's default model (if API supports it)

```bash
echo "=== Setting default model for Lilymay ==="
echo "NOTE: Open WebUI's user-settings API varies by version."
echo "If this step fails, Lilymay can select 'GCSE English Tutor' from the model dropdown manually."
echo "Once selected, Open WebUI remembers her last-used model."
echo ""
echo "To set it manually via admin: Admin Panel → Users → Lilymay → Default Model → GCSE English Tutor"
```

---

## Phase 4: Smoke test

### 4.1 API-level test — full round-trip through Open WebUI

```bash
echo "=== Smoke test: API round-trip through Open WebUI ==="

# Log in as Lilymay to get her JWT
LILYMAY_TOKEN=$(curl -s http://localhost:8080/api/v1/auths/signin \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"lilymay@local\", \"password\": \"$LILYMAY_PASSWORD\"}" \
    | python3 -c "import sys, json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

if [ -z "$LILYMAY_TOKEN" ] || [ "$LILYMAY_TOKEN" = "None" ]; then
    echo "FAIL: Could not log in as Lilymay"
    echo "Try logging in via the web UI at http://localhost:8080 to verify credentials."
    exit 1
fi
echo "Logged in as Lilymay."

# Send a test message through the model preset
CHAT_RESPONSE=$(curl -s http://localhost:8080/api/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $LILYMAY_TOKEN" \
    -d '{
        "model": "gcse-english-tutor",
        "messages": [
            {"role": "user", "content": "Help me with my Macbeth essay"}
        ]
    }')

TUTOR_TEXT=$(echo "$CHAT_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'choices' in data:
    print(data['choices'][0]['message']['content'])
elif 'error' in data:
    print('ERROR: ' + str(data['error']))
else:
    print('UNEXPECTED: ' + json.dumps(data)[:500])
" 2>/dev/null)

echo ""
echo "Tutor response (first 500 chars):"
echo "${TUTOR_TEXT:0:500}"
echo ""
```

### 4.2 Check for template-token leaks

```bash
echo "=== Checking for template-token leaks ==="
LEAK_TOKENS="<|channel> <channel|> <think> </think> <|turn> <turn|>"
LEAK_FOUND=false

for TOKEN in $LEAK_TOKENS; do
    if echo "$TUTOR_TEXT" | grep -qF "$TOKEN"; then
        echo "LEAK DETECTED: $TOKEN"
        LEAK_FOUND=true
    fi
done

if [ "$LEAK_FOUND" = true ]; then
    echo ""
    echo "FAIL: Template tokens are leaking through Open WebUI."
    echo "This means the custom Jinja template fix is not being applied."
    echo "Check: is llama-swap using --chat-template-file gemma4-tutor.jinja?"
    echo "Check: is the system prompt being double-applied (once in the Jinja template, once from Open WebUI)?"
    echo "Ref: RUNBOOK-fix-tutor-template-leak.md"
else
    echo "PASS: No template-token leaks detected."
fi
```

### 4.3 Check response quality

```bash
echo "=== Checking response quality (manual) ==="
echo ""
echo "Verify the following manually from the tutor response above:"
echo "  [ ] Response is encouraging and supportive"
echo "  [ ] Response uses Socratic method (asks guiding questions rather than giving direct answers)"
echo "  [ ] Response references AQA mark scheme criteria or exam technique"
echo "  [ ] Response is age-appropriate for a Year 10 student"
echo "  [ ] No technical jargon about models, APIs, or infrastructure"
echo ""
echo "If the response is flat, generic, or gives direct answers instead of guiding questions,"
echo "verify the system prompt was correctly baked into the model preset."
```

---

## Phase 5 (Stretch): Multi-Subject Presets

The fine-tuned model is English-only. For other subjects, the base Gemma 4 model with a subject-specific system prompt can still provide useful tutoring. Each preset uses the same `gemma4-tutor` model endpoint — llama-swap routes to the same GGUF — but with a different system prompt that shapes the behaviour for that subject.

> These won't match the fine-tuned English tutor's quality, but "base model + good prompt" is still useful for homework help. Lilymay picks the subject from the model dropdown and gets subject-appropriate guidance.

### 5.1 Create subject system prompts

Write each system prompt to a temporary file, then create the preset. All prompts share a common preamble about being a patient, Socratic GCSE tutor for a Year 10 student following the AQA specification.

```bash
echo "=== Creating multi-subject system prompts ==="

SUBJECTS_DIR="/tmp/tutor-subject-prompts"
mkdir -p "$SUBJECTS_DIR"

# --- Maths ---
cat > "$SUBJECTS_DIR/maths.txt" <<'PROMPT'
You are a GCSE Maths tutor for a Year 10 student following the AQA specification. Your approach:

- Use the Socratic method — guide the student to discover solutions through questions, don't just give answers
- Always ask the student to show their working before you help — "What have you tried so far?"
- Break complex problems into smaller steps and guide through each one
- When the student makes an error, help them find it themselves: "Look at step 3 again — does that look right to you?"
- Explain mathematical concepts using real-world examples where possible
- Emphasise method marks — in AQA exams, showing clear working earns marks even if the final answer is wrong
- Cover all AQA topics: Number, Algebra, Ratio and Proportion, Geometry and Measures, Probability and Statistics
- For calculation questions, insist on proper units and rounding as specified in the question
- Be patient, encouraging, and celebrate when the student gets something right
- If the student is stuck, give a small hint rather than the full solution — let them have the "aha!" moment
- Never be condescending — treat every question as a good question
PROMPT

# --- French (AQA 8652) ---
cat > "$SUBJECTS_DIR/french.txt" <<'PROMPT'
You are a GCSE French tutor for a Year 10 student following the AQA specification (8652 — new spec, first exams summer 2027). Your approach:

- Use the Socratic method — guide the student to discover answers, don't just give them
- Encourage use of French in your responses where appropriate, but always provide English support so the student isn't lost
- Help with vocabulary building, grammar rules, reading comprehension, and translation practice
- When correcting errors, ask the student to spot the mistake first: "Something isn't quite right in that sentence — can you see what it is?"
- Explain grammar patterns clearly — e.g. why certain verbs take être in the passé composé
- For translation practice, guide the student through the process step by step rather than giving the full translation
- Cover all four skills: Listening, Speaking, Reading, Writing (focus on what can be practised in text chat: reading, writing, grammar, vocabulary)
- Reference the AQA themes: Identity and culture, Local area and environment, School and future aspirations, International and global dimension
- Be patient and encouraging — learning a language takes time and mistakes are part of the process
- Celebrate progress and effort, not just accuracy
PROMPT

# --- Spanish (AQA 8692) ---
cat > "$SUBJECTS_DIR/spanish.txt" <<'PROMPT'
You are a GCSE Spanish tutor for a Year 10 student following the AQA specification (8692 — new spec, first exams summer 2027). Your approach:

- Use the Socratic method — guide the student to discover answers, don't just give them
- Encourage use of Spanish in your responses where appropriate, but always provide English support so the student isn't lost
- Help with vocabulary building, grammar rules, reading comprehension, and translation practice
- When correcting errors, ask the student to spot the mistake first: "Hay algo que no está bien en esa frase — ¿puedes verlo?"
- Explain grammar patterns clearly — e.g. ser vs estar, preterite vs imperfect
- For translation practice, guide the student through the process step by step
- Cover all four skills: Listening, Speaking, Reading, Writing (focus on reading, writing, grammar, vocabulary in text chat)
- Reference the AQA themes: Identity and culture, Local area and environment, School and future aspirations, International and global dimension
- Be patient and encouraging — mistakes are how you learn a language
- Celebrate progress and effort
PROMPT

# --- History (AQA) ---
cat > "$SUBJECTS_DIR/history.txt" <<'PROMPT'
You are a GCSE History tutor for a Year 10 student following the AQA specification. Your approach:

- Use the Socratic method — guide the student to discover answers through questions, don't just give them
- Help with source analysis: "What can you tell about the author's perspective? What's the provenance of this source?"
- Build chronological understanding by asking the student to sequence events before explaining their significance
- Encourage evaluation of historical interpretations — "Why do historians disagree about this?"
- For essay-style questions, help structure arguments: Point, Evidence, Explanation, Link back to the question
- When the student makes a factual error, guide them to the correct information: "That's close — but check the date again. What was happening in that year?"
- Reference key exam techniques: inference from sources, utility of sources, explaining significance, narrative accounts
- Cover AQA content areas relevant to the student's chosen modules
- Help distinguish between description (what happened) and explanation (why it happened/why it mattered)
- Be patient, encouraging, and make history feel like storytelling, not just memorising dates
- Celebrate good analytical thinking, even if the factual recall isn't perfect yet
PROMPT

# --- Biology (AQA Triple) ---
cat > "$SUBJECTS_DIR/biology.txt" <<'PROMPT'
You are a GCSE Biology tutor for a Year 10 student following the AQA Triple Science specification. Your approach:

- Use the Socratic method — guide the student to discover answers, don't just give them
- Explain scientific concepts step by step, using analogies and real-world examples
- For required practicals, walk through the method, variables (independent, dependent, control), and expected results
- When the student gives an incorrect answer, ask probing questions: "What do you think happens to the molecules when temperature increases?"
- Help with scientific terminology — explain terms clearly but insist on using proper scientific language in answers
- For exam technique, emphasise command words: describe, explain, evaluate, compare, suggest
- Cover all AQA Biology topics: Cell biology, Organisation, Infection and response, Bioenergetics, Homeostasis, Inheritance, Ecology
- Help the student understand graphs, tables, and data analysis — "What does this trend tell you?"
- Be patient, encouraging, and celebrate curiosity — "That's a great question!"
- When relevant, connect biology concepts to everyday life to make them memorable
PROMPT

# --- Chemistry (AQA Triple) ---
cat > "$SUBJECTS_DIR/chemistry.txt" <<'PROMPT'
You are a GCSE Chemistry tutor for a Year 10 student following the AQA Triple Science specification. Your approach:

- Use the Socratic method — guide the student to discover answers, don't just give them
- For balancing equations, guide step by step — don't just give the balanced equation: "How many oxygen atoms on each side?"
- Explain atomic structure and bonding using clear models and analogies
- For calculations (moles, concentration, Mr), insist on showing working and units at every step
- When the student makes an error, help them trace back: "Let's check your working from step 2 — what did you get for the Mr?"
- Help with required practicals: method, safety, variables, results interpretation
- Cover all AQA Chemistry topics: Atomic structure, Bonding, Quantitative chemistry, Chemical changes, Energy changes, Rate and extent, Organic chemistry, Chemical analysis, Chemistry of the atmosphere, Using resources
- Emphasise exam command words and mark allocation: a 6-mark question needs a detailed, structured answer
- Be patient and encouraging — chemistry can feel abstract, but it explains the physical world
- Celebrate when the student spots patterns (e.g. trends in the periodic table)
PROMPT

# --- Physics (AQA Triple) ---
cat > "$SUBJECTS_DIR/physics.txt" <<'PROMPT'
You are a GCSE Physics tutor for a Year 10 student following the AQA Triple Science specification. Your approach:

- Use the Socratic method — guide the student to discover answers, don't just give them
- For calculation questions, always guide through: identify the formula, substitute values, check units, calculate, state the answer with units
- Help the student understand physical concepts before jumping to equations — "What do you think is happening to the particles?"
- When the student makes a calculation error, help them find it: "Check your units — did you convert to SI?"
- Explain formulae conceptually, not just procedurally — "F = ma means a bigger force gives a bigger acceleration for the same mass"
- For required practicals, walk through method, variables, safety, and how to analyse results
- Cover all AQA Physics topics: Energy, Electricity, Particle model, Atomic structure, Forces, Waves, Magnetism, Space physics
- Help with graph skills: reading values, calculating gradients, interpreting areas under curves
- Insist on proper significant figures and standard form where appropriate
- Be patient and encouraging — physics is about understanding how the universe works, and that's exciting
- Celebrate effort and reasoning, even when the final number isn't quite right
PROMPT

echo "System prompts written to $SUBJECTS_DIR:"
ls -la "$SUBJECTS_DIR"
```

### 5.2 Create the presets

```bash
echo "=== Creating multi-subject model presets ==="

# Subject config: id|display_name|prompt_file|description
SUBJECTS=(
    "gcse-maths|GCSE Maths Tutor|maths.txt|Your personal GCSE Maths tutor — step-by-step problem solving with clear working."
    "gcse-french|GCSE French Tutor|french.txt|Your personal GCSE French tutor — vocabulary, grammar, translation, and reading practice."
    "gcse-spanish|GCSE Spanish Tutor|spanish.txt|Your personal GCSE Spanish tutor — vocabulary, grammar, translation, and reading practice."
    "gcse-history|GCSE History Tutor|history.txt|Your personal GCSE History tutor — source analysis, essays, and chronological understanding."
    "gcse-biology|GCSE Biology Tutor|biology.txt|Your personal GCSE Biology tutor — concepts, practicals, and exam technique."
    "gcse-chemistry|GCSE Chemistry Tutor|chemistry.txt|Your personal GCSE Chemistry tutor — equations, calculations, and practical skills."
    "gcse-physics|GCSE Physics Tutor|physics.txt|Your personal GCSE Physics tutor — forces, energy, electricity, and calculation skills."
)

PASS_COUNT=0
FAIL_COUNT=0

for SUBJECT in "${SUBJECTS[@]}"; do
    IFS='|' read -r PRESET_ID PRESET_NAME PROMPT_FILE DESCRIPTION <<< "$SUBJECT"

    echo ""
    echo "--- Creating: $PRESET_NAME ---"

    python3 - "$ADMIN_TOKEN" "$PRESET_ID" "$PRESET_NAME" "$SUBJECTS_DIR/$PROMPT_FILE" "$DESCRIPTION" <<'PY'
import sys, json, urllib.request, pathlib

token, preset_id, preset_name, prompt_path, description = sys.argv[1:6]
system_prompt = pathlib.Path(prompt_path).read_text().strip()

payload = {
    "id": preset_id,
    "name": preset_name,
    "meta": {
        "description": description,
        "profile_image_url": ""
    },
    "base_model_id": "gemma4-tutor",
    "params": {
        "system": system_prompt,
        "temperature": 0.7,
        "top_p": 0.9
    }
}

req = urllib.request.Request(
    "http://localhost:8080/api/v1/models/create",
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"PASS: {result.get('name', preset_name)}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"FAIL (HTTP {e.code}): {body[:200]}")
    sys.exit(1)
PY

    if [ $? -eq 0 ]; then
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

echo ""
echo "=== Multi-subject preset results: $PASS_COUNT passed, $FAIL_COUNT failed ==="

# Clean up
rm -rf "$SUBJECTS_DIR"
```

---

## Phase 6: Decision gate

| Step | Expected | Notes |
|---|---|---|
| P0.1: llama-swap serving gemma4-tutor | PASS | |
| P0.2: System prompt file exists | PASS | |
| P0.3: Port 8080 available | PASS | |
| P0.4: Docker available | PASS | |
| P1.1: Open WebUI container running | PASS | Health endpoint responds |
| P1.2: Admin account created | PASS | rich@appmilla.com |
| P2.3: English Tutor preset created | PASS | System prompt baked in |
| P3.1: Lilymay account created | PASS | lilymay@local |
| P4.1: Chat round-trip works | PASS | Response received through Open WebUI |
| P4.2: No template-token leaks | PASS | No `<\|channel>`, `<think>`, etc. |
| P4.3: Response quality acceptable | PASS (manual) | Socratic, encouraging, AQA-aware |
| P5.2: Multi-subject presets (stretch) | PASS | 7/7 created |

### All pass

```bash
echo "=== Setup complete ==="
echo ""
echo "Lilymay's access details:"
echo "  URL:      http://promaxgb10-41b1:8080"
echo "  Email:    lilymay@local"
echo "  Password: (shared directly with Lilymay)"
echo ""
echo "Available tutors in the model dropdown:"
echo "  - GCSE English Tutor (fine-tuned — best quality)"
echo "  - GCSE Maths Tutor"
echo "  - GCSE French Tutor"
echo "  - GCSE Spanish Tutor"
echo "  - GCSE History Tutor"
echo "  - GCSE Biology Tutor"
echo "  - GCSE Chemistry Tutor"
echo "  - GCSE Physics Tutor"
echo ""
echo "MANUAL STEP REQUIRED:"
echo "  Rich must approve Lilymay's device(s) on Tailscale admin console"
echo "  so she can reach promaxgb10-41b1:8080 from her laptop/phone/tablet."
echo ""
echo "  Alternatively, if all devices are on the same home LAN,"
echo "  she can use the GB10's local IP address directly."
```

### Rollback

```bash
echo "=== Rollback: removing Open WebUI ==="
docker stop open-webui
docker rm open-webui
# Preserve data volume in case we want to redeploy
# To fully remove: docker volume rm open-webui-data
echo "Container removed. Data volume preserved (docker volume rm open-webui-data to fully clean up)."
```

---

## Operational notes

### Updating Open WebUI

```bash
docker pull ghcr.io/open-webui/open-webui:main
docker stop open-webui && docker rm open-webui
# Re-run the docker run command from Phase 1.1
# Data persists in the open-webui-data volume — conversation history and presets survive container recreation.
```

### Monitoring

- **Logs:** `docker logs open-webui --tail 50 -f`
- **Container health:** `docker inspect open-webui --format='{{.State.Status}}'`
- **llama-swap status:** `curl -s http://localhost:9000/running | python3 -m json.tool`

### If Lilymay sees errors

1. **"Model not found"** — llama-swap may have restarted and the model alias isn't loaded yet. Wait 30 seconds and retry, or check `systemctl --user status llama-swap`.
2. **Timeout/slow response** — first request after model swap takes ~30s while llama-swap loads the GGUF. Subsequent requests are fast.
3. **Template tokens visible** — the Jinja template fix has regressed. Re-run `RUNBOOK-fix-tutor-template-leak.md`.
4. **Can't reach the page** — Tailscale not connected on her device, or GB10 is off/sleeping.

---

## Cross-references

- Conversation starter: [`study-tutor/docs/research/ideas/study-tutor-access-conversation-starter.md`](study-tutor-access-conversation-starter.md)
- Template leak fix: [`agentic-dataset-factory/domains/architect-agent-probe/RUNBOOK-fix-tutor-template-leak.md`](../../../../agentic-dataset-factory/domains/architect-agent-probe/RUNBOOK-fix-tutor-template-leak.md)
- Production deployment: [`guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md`](../../../../guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md)
- llama-swap systemd supervision: [`guardkit/docs/research/dgx-spark/llama-swap-systemd-supervision.md`](../../../../guardkit/docs/research/dgx-spark/llama-swap-systemd-supervision.md)
- System prompt source: `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt`
- llama-swap config: `/opt/llama-swap/config/config.yaml`

*Prepared: 2026-04-29*
