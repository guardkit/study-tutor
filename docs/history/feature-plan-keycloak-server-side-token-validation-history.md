# /feature-plan — keycloak-server-side-token-validation — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-plan keycloak-server-side-token-validation — 2026-07-08T19:53:18Z

### Prompt

```
/feature-plan "Keycloak Server-Side Token Validation" \
  --context features/keycloak-server-token-validation/keycloak-server-token-validation_summary.md \
  --context docs/design/keycloak-auth-user-management-design.md
```

### Assistant response

I'll execute the `/feature-plan` workflow for "Keycloak Server-Side Token Validation". Let me start by reading the provided context files and understanding the existing conventions in this repo.

Now let me read the full BDD feature spec, the assumptions, the sibling review task (for convention), and the actual `auth.py` seam being modified.

Let me examine the actual code seam being modified and the sibling feature's IMPLEMENTATION-GUIDE for convention.

Let me check the task-file convention (a sibling task + README) and how the auth config is wired into the app/WS composition.

Let me see the app factory (where auth_config is built) and the CLI boot path, to place the mode-selection/fail-fast correctly.

I now have a thorough understanding of the A2 slice: the `TokenResolver` seam (KC-D6), the `auth.py` code that keeps its outer contract, the new `auth_keycloak.py` sibling module, the env-driven mode selection with boot fail-fast, the AC-005 tripwire re-scope, and the WS/dev-reset/live-suite couplings. The design is ratified and the 25-scenario spec is operator-confirmed.

Proceeding with the `/feature-plan` workflow. First, **Context A — Review Scope Clarification**.

Context A recorded: **focus = security_quality**, **trade-off = quality** (matching the A1 slice). Let me verify the AutoBuild tooling is available and create the review task, then present the analysis.

Tooling confirmed (`generate-feature-yaml`, `feature-plan-bdd-link`, `guardkit` CLI all present). Now presenting the decision review.

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING: Keycloak Server-Side Token Validation (FEAT-AUTH-002, A2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Review task: TASK-REV-KCA2  ·  Focus: security & correctness  ·  Trade-off: quality
Depth: standard  ·  Context: A2 summary + design KC-D1…D7 + auth.py seam
```

## 🔍 Decision Review — the A2 server slice

The architecture is **already ratified** (design KC-D6, operator-confirmed spec, ADR-ARCH-028). So this review is not choosing an architecture — it confirms the recommended **shape** and surfaces the genuine decision points, risks, and task breakdown through a security lens.

### The seam (fixed by KC-D6)
`resolve_student_from_token` in [auth.py](src/study_tutor/http/auth.py) keeps its **outer contract byte-for-byte** — (1) Bearer extraction, (3) unseeded-student guard — and delegates only **step 2** (the derivation source) to an injected `TokenResolver` (`async resolve(token) -> student_id`, raises `Unauthenticated`). `TableTokenResolver` stays in `auth.py`; `KeycloakTokenResolver` lands in a **new sibling** `http/auth_keycloak.py`. Both [app.py](src/study_tutor/http/app.py#L88) `_resolve_student_id` and [ws.py](src/study_tutor/http/ws.py#L140) already call the same function, so **WS inherits the resolver for free** (binding §2.1).

### The one genuine design choice — how the resolver is threaded
| Option | How | Verdict |
|---|---|---|
| **1. Resolver carried on `HTTPAuthConfig` (Recommended)** | Boot builds the selected resolver; `HTTPAuthConfig` gains a `resolver` field; `resolve_student_from_token(header, config, store)` signature **unchanged** — callsites in app.py/ws.py untouched | ✅ Zero change to the frozen callsites; delegation is internal; table mode stays byte-for-byte |
| 2. Resolver on `app.state`, new param | Thread resolver as a new arg through `_resolve_student_id` | ⚠️ Changes two callsites + WS; widens the contract surface for no gain |
| 3. Module-level mode switch inside `resolve_student_from_token` | `if AUTH_MODE == …` branch inline | ❌ Puts JWT concerns back in auth.py — violates the AC-005 tripwire |

**Recommended: Option 1** — keeps `auth.py` JWT-free forever, keeps the frozen contract's function signature intact, isolates all Keycloak/PyJWT imports in the sibling module.

### Security surface (the focus lens) — what the KeycloakTokenResolver must get right
- **Signature** via `PyJWKClient` (cached, kid-rotation aware); **`iss`** pinned to the ts.net issuer even when JWKS is fetched by tailnet IP (KC-D2 `extra_hosts` gotcha); **`aud`** verified; **`exp`/`nbf`** with the operator-confirmed **60 s** leeway (ASSUM-001).
- **Algorithm allowlist — asymmetric only (RS256).** The classic JWKS attack is alg-confusion (`alg: none` / HS256 signed with the public key). Must be an explicit allowlist, not a denylist.
- **Fail-closed everywhere**: unknown-kid, unreachable JWKS, missing `student_id` claim, garbage Bearer → `Unauthenticated`, **never a 500** (a mis-provisioned attribute must be a clean 401 — KC-D3/ASSUM-001).
- **Boot fail-fast (SystemExit)** on incomplete keycloak config (issuer+audience required — ASSUM-002/005) and on an **unknown `STUDY_TUTOR_AUTH_MODE`** value (ASSUM-007) — matching the DSN discipline at [cli/main.py:869](src/study_tutor/cli/main.py#L869).
- **Tripwire re-scope**: `test_no_keycloak_jwt_imports` stays green for `auth.py`; the imports must now live **only** in `auth_keycloak.py`. Plus: `/__dev__/reset` and keycloak mode must never coexist.

### Effort / complexity / risk
- **Complexity: 8/10** (security-critical, driven by the JWKS validation core) · **Est. ~7–8 h** authorable + 1 operator gate
- **Risk: Medium-High** — mitigated by hermetic RSA-minted-key tests (no live infra needed for the security scenarios) and a flag-gated default (`table` everywhere → **merging A2 changes nothing in prod**).
- **Notable**: this slice **wires the JWKS read path that A1 deliberately left `NOT WIRED`** — no disconnected paths remain.

### Proposed breakdown — 7 tasks, 5 waves

```
Wave 1  TASK-KCA2-001  PyJWT[crypto] dep + OIDCSettings (env surface, fail-fast helper)   declarative  c4
        TASK-KCA2-002  TokenResolver protocol + TableTokenResolver refactor (auth.py)     refactor     c6
Wave 2  TASK-KCA2-003  KeycloakTokenResolver in http/auth_keycloak.py + hermetic tests    feature      c8
Wave 3  TASK-KCA2-004  Boot wiring: AUTH_MODE select + fail-fast + thread resolver         feature      c5
Wave 4  TASK-KCA2-005  AC-005 tripwire re-scope + dev-reset/keycloak coexistence guard     testing      c3
        TASK-KCA2-006  Live-suite token-minting harness (skips w/o live realm)             testing      c5
Wave 5  TASK-KCA2-007  KC-G2 gate: live dev deploy, live-suite green, hermetic green       operator_handoff c5
```
**§4 contracts:** `OIDC_SETTINGS` (001→003,004), `TOKEN_RESOLVER` protocol (002→004). No intra-wave dependencies.

---

Now the decision checkpoint.

Decision: **Implement** · Option 1 (resolver on `HTTPAuthConfig`) · detect waves · standard tests. Let me check the YAML generator's options (to pin `FEAT-AUTH-002`) and the BDD-linker's `prepare` contract.

Decision recorded. Generating the full feature structure now. Let me start with the review task and the first three task files.

Now the README and the IMPLEMENTATION-GUIDE with the mandatory Mermaid diagrams.

All 10 files written. Now generating the structured `FEAT-AUTH-002` YAML with `--discover` (resolves `file_path` from the actual files on disk).

YAML generated (7 tasks, 5 waves). AC-quality: **0 unverifiable**. The R3 smoke-gates nudge fired — given the quality trade-off, I'll add a between-wave smoke gate targeting the auth composition. Let me read the YAML and inject it.

The YAML looks correct (7 tasks, 5 waves, no intra-wave deps). Now injecting the smoke gate. `tests/unit/http` exists on disk (spatially valid); `test_auth_keycloak.py` is created in wave 2, so firing after waves 3 & 4 is temporally safe.

Now the pre-flight validations (step 8.5 feature validate + step 8.6 smoke-gate validator):

Both validators pass. The `feature validate` warning notes wave 5 isn't gated — but wave 5 is the single `operator_handoff` KC-G2 task (no AutoBuild code lands there), so there's nothing to gate. Let me document that rationale in the YAML comment so the deliberate choice is clear.

Now **Step 11 — BDD scenario linking**. Running `prepare` to build the matching request for the 25 scenarios.

`prepare` is ready: 25 scenarios, 7 tasks, 0 already tagged. Now invoking the `bdd-linker` subagent to map scenarios → tasks (it reads the request file and returns `TaskMatch[]`).

The `bdd-linker` returned matches for all 25 scenarios. Writing the response and running `apply` to tag the `.feature` file with `@task:` tags.

The `apply` hit a JSON parse error ("Extra data (line 31 column 1)"). Let me inspect exactly what the parser sees.

The Write leaked a literal `</content>` line into the file. Let me rewrite it cleanly via heredoc and re-run `apply`.

Step 11 succeeded: **all 25 scenarios linked, 0 below threshold**. Let me verify the tags landed and confirm the final state of the generated artifacts.
