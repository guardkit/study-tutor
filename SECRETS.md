# SECRETS.md — how credentials work in this repo (BINDING)

> For every human and every agent session in study-tutor. The fleet has a secrets
> vault — **sops + age, decision DF-022** — with per-machine keys and a
> YubiKey-guarded offline escrow; this repo's env files are already migrated
> (gates green 2026-07-30). Every credential that lands in a repo mints an
> exposure record plus an attended rotation Rich has to carry. Use the vault.

## 1. The iron rules

1. **No credential VALUE ever enters a repo — the rule follows the value, not the
   location.** No bearer/access/refresh tokens, passwords, client secrets, API
   keys, or DSNs with embedded credentials in: code, tests, fixtures, docs, task
   files, compose/YAML, `.env.example` files, commit messages, PR bodies, issue
   comments, handoff/register pages in **ai-transition or any sibling repo**, or
   pasted terminal transcripts. When quoting a command or output anywhere,
   replace every value with `<REDACTED>` first. This includes machine-written
   captures: never commit recorded live HTTP traffic (VCR/cassette fixtures, HAR
   files, proxy dumps — recorders must filter `Authorization` headers and
   token-endpoint bodies); `.http`/`.rest` files use `{{variable}}` references,
   never literals; notebooks are committed with outputs cleared. Committed files
   carry **ref names only** (the name `STUDY_TUTOR_PG_DSN`, never its value).
2. **Keycloak bearer tokens are never stored ANYWHERE — not even in the vault.**
   They expire by design. Anything needing a token **mints it at runtime** from
   the token endpoint using vault-supplied config (§4). Unit tests needing a JWT
   *shape* construct an obviously-fake one in the test.
3. **Never print a secret value to the terminal.** The only sanctioned way to
   inspect env surfaces is **names-only**: `printenv | cut -d= -f1 | sort` (same
   for `docker inspect` output — extract names, never values). Never pipe auth
   traffic, token responses, or `curl -v` output through a grep filter and call
   it safe — the fleet's minimum filter has already been shown to pass DSNs and
   `Authorization: Bearer` lines. If a values-context is truly unavoidable, the
   floor is `grep -viE 'password|token|secret|bearer|authorization|_key|_dsn|_url|eyJ[A-Za-z0-9_-]{10,}|://[^/ ]*:[^/ ]*@'`
   — and it is a last-resort screen, not a license.
4. **Secrets move via env or stdin, never argv, never stdout.** No
   `psql postgresql://user:pass@…` on a command line; no `sops set` with the
   value as an argument.
5. **Rotation and value-handling are attended, operator work — Rich present.**
   Agents never rotate, revoke, or re-issue a credential, and never hold a raw
   value in context: name the ref, wire `${NAME:?}` into code/compose, and hand
   value-insertion to Rich (§5). The runbook is the register's study-tutor family
   page (§8), grammar R2a→R2→R3→R4.
6. **If a value leaks anyway** (file, commit, PR body, terminal): STOP. Tell Rich
   immediately, name the file/commit. Do not silently scrub history, do not
   rotate yourself. A leak is an exposure event with its own register row; hiding
   it is worse than the leak.
7. **Before every commit**, this must return nothing:
   `git diff --cached | grep -nE 'eyJ[A-Za-z0-9_-]{20,}|Authorization: *Bearer|client_secret|://[^/ ]*:[^/ ]*@'`
   Any hit is a rule-6 STOP — never fix-and-recommit silently. (Hits inside
   SECRETS.md itself are pattern text, not values — exempt.)

## 2. Where secrets actually live — the fleet vault

First, know which box you are on: `uname -s` = `Darwin` → the Mac; otherwise
`hostname` → `promaxgb10-41b1` = GB10 / Node A; `spark-*` / `dgx-spark` = the
Spark / Node B.

Encrypted env files live in a per-machine, **out-of-repo** secrets root:
`~/.config/fleet-secrets/` (mode 700). Vault files — plaintext AND ciphertext —
never enter a git worktree. Each machine's `age` private key is born on that
machine and never travels; every file is also encrypted to `age-escrow` (offline,
YubiKey-guarded, recovery drill green 2026-07-30), so machine loss is
recoverable. Never invent your own backup channel.

| Machine | Role for study-tutor | Secrets root | age key | sops binary |
|---|---|---|---|---|
| **Spark / Node B** (`spark-fcf6`) | Deployment host since 2026-07-30 (`study_tutor_http` :8100 + `study_tutor_http_kc` :8101) | `~/.config/fleet-secrets/study-tutor/` | `~/.config/sops/age/keys.txt` | `~/.local/bin/sops` (absolute path in scripts) |
| **GB10 / Node A** (`promaxgb10-41b1`) | Original host; its containers + enc files stand until the move lane decommissions them | `~/.config/fleet-secrets/study-tutor/` | `~/.config/sops/age/keys.txt` | `~/.local/bin/sops` |
| **Mac** (dev laptop) | `age-mac` key is LIVE but there is **no secrets root here yet** — create it on first real need (§6) | — | `~/Library/Application Support/sops/age/keys.txt` | `/opt/homebrew/bin/sops` |
| **NAS** (`whitestocks`) | Runs the actual `study_tutor_postgres` (:5434). Its rendered `.env` (`POSTGRES_PASSWORD`) is **deliberately plaintext-600** — a recorded v1 deferral, not a leak. Don't "fix" it. | (root exists, empty in v1) | — | `~/bin/sops` (absolute — non-interactive SSH PATH won't find it) |

**Study-tutor's encrypted files:**

| File (under the root's `study-tutor/`) | Where | What it feeds |
|---|---|---|
| `http-env.enc.env` | Node B (and GB10 until decommission) | the :8100 Session API (`STUDY_TUTOR_HTTP_TOKENS` table, `STUDY_TUTOR_PG_DSN`) |
| `http-env-kc.enc.env` | Node B | the :8101 **Keycloak/OIDC** project (`STUDY_TUTOR_AUTH_MODE`, `STUDY_TUTOR_OIDC_*`; token table empty by design) |
| `study-tutor-root.enc.env` | GB10 | the gcse-tutor NATS subscriber (NATS creds, PG DSN) |
| `postgres-env-deploy.enc.env` | GB10 | the NAS Postgres deploy runbook (PG password source of truth) |
| `keycloak-env-deploy.enc.env` | GB10 | Keycloak **server** deploy/provisioning creds (KC DB, bootstrap-admin + user passwords, NAS connection fields) — sourced dual-mode by `deploy/keycloak/provision-live-suite.sh` |

**Sanctioned in-worktree plaintext (gitignored, tolerated — never tracked):**
the dual-mode scripts prefer a plaintext `deploy/keycloak/.env.deploy` while one
exists, and `provision-live-suite.sh` writes `deploy/keycloak/.env.live-suite`
(the live-suite client secret). These stay gitignored — `.gitignore` covers
`.env`, `.envrc`, `.env.deploy`, `.env.kc`, `.env.live-suite`; never weaken those
rules.

## 3. Reading secrets at runtime — `sops exec-env`, from the root

Two laws govern every sops invocation:

- **Run from the secrets root** (`cd ~/.config/fleet-secrets` first, or pass
  `--config ~/.config/fleet-secrets/.sops.yaml`). sops discovers `.sops.yaml`
  upward from the **working directory** — run from inside a repo it can silently
  pick the wrong rules and encrypt to the wrong recipients.
- **`sops exec-env` is the primary shape** — decrypts straight into the child
  process environment; no plaintext file ever exists. Never `sops -d > .env`.

```sh
cd ~/.config/fleet-secrets
# start/recreate a service (compose interpolates ${VAR:?} from the process env):
sops exec-env study-tutor/http-env.enc.env \
  'docker compose -f /abs/path/to/study-tutor/deploy/http/docker-compose.yml up -d study_tutor_http'
# run a repo command that needs the env — the inner cd back into the repo is REQUIRED
# (uv/pytest resolve the project from cwd; run from the secrets root they collect nothing):
sops exec-env study-tutor/http-env-kc.enc.env \
  'cd /abs/path/to/study-tutor && uv run pytest -m keycloak -q'
# see what a file provides — NAMES ONLY, never values:
sops exec-env study-tutor/http-env-kc.enc.env 'printenv | cut -d= -f1 | sort'
```

**From the Mac, when the file lives on the Spark:** running sops remotely on the
box that holds the key is the sanctioned shape — decryption stays on-box and
nothing but names/exit codes comes back over the channel:
`ssh <spark-alias> 'cd ~/.config/fleet-secrets && ~/.local/bin/sops exec-env study-tutor/<file>.enc.env "<command>"'`
(the Mac's ssh config carries a Spark alias; verify reachability at run time).
Never `ssh box 'sops -d …'` back to your terminal.

If a literal on-disk file is truly unavoidable, the sanctioned fallback is a 0600
file under `/run/user/$UID/` with a trap-`rm` (Linux boxes only) — wrapper
templates in the vault docs (§8). `sops exec-file` is a known trap (its temp path
is not controllable); do not use it.

## 4. Keycloak: the pattern that keeps going wrong, and the right one

**Never store a bearer token anywhere — mint at runtime.** That is the whole
rule; everything below is mechanics.

- The OIDC **client config** (`STUDY_TUTOR_AUTH_MODE`, `STUDY_TUTOR_OIDC_*`)
  lives in `http-env-kc.enc.env` (Node B). Keycloak **server/provisioning** creds
  live in `keycloak-env-deploy.enc.env` (GB10). Code and tests read config from
  the process environment only.
- `tests/integration/test_keycloak_contract.py` is the model: it mints tokens at
  runtime (Direct Access Grant against the issuer's token endpoint) from env
  config. **Its live tests additionally need the `STUDY_TUTOR_LIVE_SUITE_*`
  surface** (client id, client secret, users map) — without those they **skip
  silently**: a green `-m keycloak` run with 0 live tests executed proves
  nothing. Set **`STUDY_TUTOR_REQUIRE_LIVE_KEYCLOAK=1`** to turn that skip into a
  loud collection error (added 2026-08-15) — use it whenever a live run is meant
  to prove something. That surface comes from the gitignored
  `deploy/keycloak/.env.live-suite`, generated by
  `deploy/keycloak/provision-live-suite.sh`. **The shape mismatch is fixed
  (2026-08-15):** the script writes a comma list of usernames and keeps passwords
  in `.env.deploy` — the more hygienic half — so the harness now accepts *both* a
  comma list (resolving each password from `<USERNAME>_PASSWORD`, the convention
  the script already uses) and the original JSON map. Pinned hermetically by
  `tests/unit/test_live_suite_users_shape.py`, so the two halves cannot drift
  apart again.
- **Proven end-to-end 2026-08-14** (was "not probed yet" — that caveat is spent).
  Lilymay's own handset (`SM-A155F`) runs a keycloak build against `:8101`: real
  browser sign-in, her student model and transcript over an authenticated
  session, a real tutor turn, and then a full **spoken** session with the robot in
  the same sitting. `:8101` carries authenticated text and voice from a real
  client. See THE PLAN ruling #12.
- **Flutter:** the app is a **public OIDC client** — it must never carry the
  OIDC client secret or any Keycloak token, in code or via `--dart-define`.
  **`STUDENT_TOKEN` is no longer part of the phone build** (2026-08-14): Lilymay's
  handset is a keycloak build and carries **no bearer at all**, so a phone rebuild
  needs no credential and rotation is a server-side act. The define survives only
  for table-mode builds (the robot's path, and any dev handset still on `:8100`).
  Precisely-bounded exception for the **table-token** bearers the live workflow
  still uses (`SUITE_TOKEN`, and `STUDENT_TOKEN` for a table build): they may be
  passed as
  `--dart-define=SUITE_TOKEN="$SUITE_TOKEN"` — a **variable expansion inside a
  child shell that got the value from the env** (sops exec-env or a sourced
  gitignored file) — never a literal token on any command line, in any script,
  shell profile, doc, or quoted transcript.
- **Debugging auth live (a 401 hunt):** mint into a shell variable only —
  `TOKEN=$(curl -sf … | jq -r .access_token)` — never echo it; never `curl -v`
  or `--trace` a token-bearing request; pass the header via stdin
  (`curl -H @- <<<"Authorization: Bearer $TOKEN"`), never as an argv literal
  (argv is visible in `ps` and shell history). The transcript of any auth
  exchange — including failure output from the `-m keycloak` suite — is itself
  secret: never paste it into a file, commit, PR, or handoff.

## 5. Adding or changing a secret

1. **Name it** — a ref name (`SCREAMING_SNAKE`), wired into code/compose as
   `${NAME:?}` or an `os.environ` read. The name is committed; the value never is.
2. **Value insertion is operator work (Rich, attended):** from the secrets root
   on the consuming machine, `sops study-tutor/<file>.enc.env` opens the editor
   over decrypted content and re-encrypts on save — the value moves via the
   editor buffer, never argv, never a repo file. **Agents: stop at step 1 and
   hand over** — an agent session never holds the raw value at all.
3. **Cross-machine need is a recipient-set question, never a copy question:** on
   a machine that **already decrypts the file**, add the new machine's `age`
   public key (from `PAGE-age-keys.md`, §8) to the file's rule in that root's
   `.sops.yaml`, run `sops updatekeys study-tutor/<file>.enc.env` **there**, then
   copy the **ciphertext** to the new machine's root (ciphertext is safe over any
   channel; still never committed). Keep the per-machine `.sops.yaml` copies in
   agreement. If no reachable box can decrypt the file: STOP and ask Rich —
   escrow recovery is operator-only.
4. **Record it** — every credential belongs to a register family page; for this
   repo that is `PAGE-study-tutor.md` in ai-transition (§8): name, location,
   consumers, rotation notes. A secret the register doesn't know about is how
   blast radius gets lost.

## 6. Mac ↔ Spark: there is no ssh-copy dance

- **Never** ssh/scp a plaintext secret between machines, and never relay a value
  through a repo file, a shell profile, or a pasted terminal.
- Need the secret's *effect* on the other box? Run the command there via remote
  `sops exec-env` (§3). Need the secret *itself* on the other box? That's §5
  step 3 — recipients + ciphertext copy.
- **The Mac's secrets root does not exist yet.** Flutter live runs are a Mac
  workload, so the first time one genuinely needs a real value: create the root
  then and there — on the Spark/GB10 add `age-mac` to the file's rule +
  `sops updatekeys` (§5 step 3), then on the Mac
  `mkdir -m 700 ~/.config/fleet-secrets`, instantiate `.sops.yaml` from the
  template (§8), copy the ciphertext over. Do **not** park values in repo files
  or profiles "temporarily" while putting this off.

## 7. Known findings — do not repeat, do not "fix" unilaterally

- `deploy/http/.env.validation` is git-tracked (a `.gitignore` negation) and
  **frozen**: a standing register DISCOVERY (its 2026-08-14 header claims
  placeholders-by-design; the register row is still open — Rich to confirm and
  close). Never add, edit, or copy entries in it; new validation config goes
  through the vault.
- The PG deploy runbook (`docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md`)
  interpolates a credential-embedding DSN into `psql` argv — a recorded open
  finding deferred to the PG-rotate lane. Don't run that pattern anywhere else,
  and don't fix the runbook in place.
- ~~The `STUDY_TUTOR_LIVE_SUITE_USERS` shape mismatch~~ **fixed 2026-08-15** (§4):
  harness accepts both shapes, hermetic test pins it, and
  `STUDY_TUTOR_REQUIRE_LIVE_KEYCLOAK=1` stops a zero-live-test run reporting green.

## 8. The canonical vault docs (ai-transition, sibling checkout on Mac + GB10)

**Working set** (what a session actually needs):

- `docs/secrets-register/PAGE-study-tutor.md` — this repo's credential family
  page: every copy, consumer, rotation gate, and the cutover history.
- `docs/secrets-register/wrappers/README.md` — launch-wrapper doctrine.
- `docs/secrets-register/secrets-root-template/README.md` — root layout +
  `.sops.yaml` template + the run-from-secrets-root law.

Background: `docs/secrets-register/README.md` (register index) ·
`docs/decisions/DECISION-DF-022-secret-storage-layer-sops-age.md` (the decision) ·
`docs/secrets-register/PAGE-age-keys.md` (key inventory, public keys) ·
`docs/secrets-register/age-key-custody-design-2026-07-11.md` (custody model) ·
`docs/secrets-register/escrow-ceremony-checklist.md` (the YubiKey ceremony).

The Spark carries no ai-transition checkout — read these from the Mac/GB10
checkout (or the git remote); don't clone ai-transition onto the Spark for this.
