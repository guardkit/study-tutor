# /feature-plan — keycloak-idp-standup-on-the-nas-feat-auth-001-a1 — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-plan keycloak-idp-standup-on-the-nas-feat-auth-001-a1 — 2026-07-08T19:27:04Z

### Prompt

```
/feature-plan "Keycloak IdP Standup on the NAS (FEAT-AUTH-001, A1)" \
      --context features/keycloak-idp-standup/keycloak-idp-standup_summary.md
```

### Assistant response

I'll execute the `/feature-plan` workflow for "Keycloak IdP Standup on the NAS". Let me first load the context file and understand the feature.

Let me read the full feature file, assumptions, and the related design/ADR documents.

This is a well-specified feature. Let me read the key design/architecture references to ground the plan in the actual codebase patterns.

Now let me examine the existing deploy patterns this feature mirrors — the Postgres deploy runbook, backup.sh, and the deploy directory structure.

Let me read the Postgres deploy runbook, its docker-compose, and backup.sh — the exact patterns this feature mirrors.

I now have deep context: the feature spec (25 scenarios, 6 smoke), the design (KC-D1…D7), ADR-ARCH-028, and the concrete patterns this mirrors — the Postgres deploy runbook's G0–G7 gate model, [backup.sh](deploy/postgres/backup.sh) (atomic pg_dump + 14-day retention), and [docker-compose.yml](deploy/postgres/docker-compose.yml).

A key observation: this is an **operator + agent standup** feature. The *deliverables* are largely committable artifacts (compose, realm-as-code JSON, backup.sh extension, the runbook), but the *gate verification* (KC-G1: device browser reaches https realm, RAM recorded before/after, cert renewal) is runtime-observed on live NAS hardware — textbook `operator_handoff` territory per this command's own detection rules.

Before I run the review analysis, let me confirm scope and the two structural forks that shape the recommendation.

All three recommendations accepted: **security+quality** review lens, **runbook + committable artifacts** (defer deploy.sh/smoke.sh), and **operator_handoff** for live tasks. Let me pull two last grounding artifacts — the lpa-poc validation reference (realm mapper mechanics) and a recent task-file format — then present the review.

Let me grab one real task markdown file to match the repo's frontmatter/body convention exactly.

I now have full grounding — the feature spec, design (KC-D1…D7), ADR-028, the lpa-poc reference (realm mapper + issuer-split mechanics), the exact task-file convention, and the Postgres deploy patterns this mirrors. Here is the review analysis.

---

## 🔍 FEATURE PLANNING: Keycloak IdP Standup on the NAS (FEAT-AUTH-001, A1)

**Review task:** `TASK-REV-KCA1` · **Mode:** decision · **Depth:** standard · **Lens:** security + quality
**Feature id:** `FEAT-AUTH-001` · **Aggregate complexity:** 6/10 (Medium) · **Risk:** Medium (single residual: DSM `tailscale cert` path)

### What this slice is

The **A1 standup slice only** — bring `study_tutor_keycloak` up on the NAS with realm-as-code, tailnet TLS, a co-located `keycloak` DB, and backups, passing gate **KC-G1**. It mirrors the proven [Postgres deploy runbook](docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md) G0–G7 gate model. Out of scope: A2 server `TokenResolver`, A3 app OIDC, A4 robot device-grant.

### Architecture — ratified, not re-opened

The load-bearing decisions are already ratified in [ADR-ARCH-028](docs/architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md) and the [design](docs/design/keycloak-auth-user-management-design.md), so the review does **not** re-litigate them:

- **Placement** (KC-D1): own `study_tutor_keycloak` container, `keycloak` DB co-located in `study_tutor_postgres` (D4 rule separates *projects*, not a project's own services). NAS RAM documented at 8 GB.
- **TLS/issuer** (KC-D2): `tailscale cert` mount, issuer pinned to `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`, with two ordered fallbacks (`tailscale serve` → GB10).
- **PII posture** (KC-D3): realm/clients/roles/mappers in git; **users & secrets never in git**.

### Technical options — the one genuine open fork

Everything else is design-decided; the only real authoring choice is **how prod-vs-dev realm separation is committed** (the spec asserts both *"live-suite present"* and *"live-suite absent from the production realm"*):

| Option | Approach | Assessment |
|---|---|---|
| **1 — Prod-safe base + runbook dev additions** ★ | Commit one prod-safe realm JSON (`study-tutor-app` + `reachy-robot` + roles + mapper; **no** live-suite, no users, no secrets). The dev-realm `live-suite` confidential client + Alex test user are runbook-created at dev standup only. | **Recommended.** Keeps the committed artifact prod-safe by construction — the "live-suite absent from prod" and "no secrets in git" negatives pass by *grep*, not by convention. Matches KC-D3 exactly. |
| 2 — Two committed realm files | `study-tutor-realm.json` (prod) + `study-tutor-realm.dev.json` (adds live-suite). | More reproducible dev realm, but risks a confidential client's secret placeholder drifting into git; larger surface. |
| 3 — One realm + prod-strip step | Commit realm *with* live-suite, strip at prod import. | Rejected — a strip step that can silently no-op is exactly the failure the negative scenario guards against. |

### Recommended approach → 6 tasks, 4 waves

Committable artifacts are autobuild-suitable; the **live standup + KC-G1 gate is `operator_handoff`** (per your choice — runtime-observed on live NAS/browser/RAM, which Coach cannot verify).

| Task | Type | Wave | What |
|---|---|---|---|
| **TASK-KC-001** | scaffolding | 1 | `deploy/keycloak/` compose + `.env.deploy.example` — pinned `26.6.x`, `start --optimized`, 2 GB limit, cert-file mounts, `--import-realm`, `KC_DB` → keycloak DB, `extra_hosts`, bootstrap admin from env, healthcheck |
| **TASK-KC-002** | declarative | 1 | `deploy/keycloak/realm/study-tutor-realm.json` — realm, clients, roles `student`+`parent`, `student_id` attribute→claim mapper, pinned ids, **no users/secrets/live-suite** |
| **TASK-KC-003** | feature | 1 | keycloak DB + least-privilege non-superuser role bootstrap SQL (owns only `keycloak` DB; cannot read learner tables) |
| **TASK-KC-004** | feature | 2 | `deploy/postgres/backup.sh` second `pg_dump -d keycloak` block — atomic, PGDMP-magic check, shared 14-day retention, **fails the run if *either* dump fails** |
| **TASK-KC-005** | documentation | 3 | `RUNBOOK-study-tutor-keycloak-standup.md` — KC-G1 gate model, cert mint + ordered fallbacks, network posture, "what NOT to do" |
| **TASK-KC-006** | **operator_handoff** | 4 | Live NAS standup + KC-G1 gate — cert mint, deploy, import-realm, user creation (never in git), RAM before/after, device browser reaches https realm |

**§4 Integration Contracts** exist (KC-D3 keycloak DB → Keycloak JDBC consumer; realm JSON → `--import-realm` consumer), so the guide will pin the exact `jdbc:postgresql://study_tutor_postgres:5432/keycloak` form and mount path.

### Risks
- **DSM `tailscale cert`** — the single residual risk (ADR-028); mitigated by the runbook's `tailscale serve` fallback (spec edge scenario covers it).
- **Deferred read path (not a bug):** the token-validation JWKS read is **A2 scope** — the data-flow diagram will mark it `NOT WIRED (deferred → A2/KC-G2)` with an explicit note, not a wiring task.

**Implement** selected. Proceeding with Option 1 (prod-safe realm base), auto-detected waves, and standard testing depth. Creating the feature structure now — 6 task files, IMPLEMENTATION-GUIDE with mandatory diagrams, README, review record, and the feature YAML.

Let me write the six task files.

Now the IMPLEMENTATION-GUIDE with the mandatory Mermaid diagrams and §4 Integration Contracts, plus the README.

Now the review-task provenance record and the feature YAML. Let me check whether the generator script exists first.

Both tools are available. Let me write the review-provenance record, then run the generator with `--discover`.

Feature YAML generated cleanly — waves match the plan, **0 unverifiable ACs**. Now the pre-flight validation (Step 8.5) and BDD scenario linking (Step 11).

Feature validates clean. Now Step 11 — link the 25 Gherkin scenarios to tasks (`@task:` tags). Let me run the `prepare` subcommand.

`ready` — 25 scenarios, 6 tasks. Let me read the request payload and invoke the `bdd-linker` subagent to map scenarios → tasks.

Now I'll invoke the `bdd-linker` subagent to produce the scenario→task mapping (it must run synchronously — I need its output for `apply`).

Strong mapping — all 25 scenarios above the 0.6 threshold. Let me write the response and run `apply`.

All 25 scenarios tagged (R2 BDD oracle now active). Let me verify the tags landed and confirm the final artifact set.
