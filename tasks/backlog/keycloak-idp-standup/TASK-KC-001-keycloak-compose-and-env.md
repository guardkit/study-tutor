---
id: TASK-KC-001
title: "study_tutor_keycloak container — deploy/keycloak compose + pinned optimized build + .env.deploy.example"
task_type: scaffolding
parent_review: TASK-REV-KCA1
feature_id: FEAT-AUTH-001
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
consumer_context:
  - task: TASK-KC-003
    consumes: KEYCLOAK_DB
    framework: "Keycloak 26.6 JDBC (start --optimized)"
    driver: "org.postgresql (KC_DB=postgres)"
    format_note: "KC_DB_URL=jdbc:postgresql://study_tutor_postgres:5432/keycloak; KC_DB_USERNAME=keycloak; intra-network port is 5432 (host maps 5434→5432), NOT host :5434 — keycloak reaches Postgres over the shared docker network by service name, or via NAS host :5434 if networks are not shared"
  - task: TASK-KC-002
    consumes: REALM_IMPORT
    framework: "Keycloak 26.6 --import-realm"
    driver: "kc.sh start --optimized --import-realm"
    format_note: "realm JSON dir mounted read-only to /opt/keycloak/data/import; realm imported on start; realm/client id fields are pinned by the producer to prevent sub-drift across down/up"
---

## Description

Create `deploy/keycloak/` and stand up the `study_tutor_keycloak` container as a
committable artifact set, mirroring the `deploy/postgres/` shape
([docker-compose.yml](../../../deploy/postgres/docker-compose.yml)). Per
[ADR-ARCH-028](../../../docs/architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md)
D1/D2 and design KC-D1/D2:

- **Image pinned** to `quay.io/keycloak/keycloak:26.6.x` (a specific 26.6 patch,
  **never** a floating `:latest`/`:26` tag). Because the design mandates
  `start --optimized`, the optimized build step (`kc.sh build --db=postgres
  --health-enabled=true`) must be baked — either via a small pinned
  `deploy/keycloak/Dockerfile` (`FROM quay.io/keycloak/keycloak:26.6.x`) that
  compose builds from, or an equivalent pre-build. The running command is then
  `start --optimized --import-realm`.
- **Memory limit** `mem_limit: 2g` (design KC-D1 band is 1–2 GB; 750 MB official
  minimum). `mem_limit` is the reliable single-host knob (not `deploy.resources`,
  which `docker compose up` ignores off-swarm).
- **TLS** via mounted `tailscale cert` files: `--https-certificate-file` /
  `--https-certificate-key-file`, https on **8443**; hostname pinned so the
  advertised issuer is `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`
  (`KC_HOSTNAME` / `KC_HOSTNAME_STRICT` per the optimized-start convention).
- **DB** points at the co-located `keycloak` database (TASK-KC-003) — see the
  §4 KEYCLOAK_DB contract; keycloak joins the existing `study_tutor_postgres`
  network (external network reference) or connects via NAS host `:5434`.
- **Realm import** mounts `./realm` → `/opt/keycloak/data/import` read-only and
  runs with `--import-realm` (see the §4 REALM_IMPORT contract).
- **Bootstrap admin** from env only (`KC_BOOTSTRAP_ADMIN_USERNAME` /
  `KC_BOOTSTRAP_ADMIN_PASSWORD`) — **never committed**; `.env` is gitignored and
  `chmod 600` on the NAS, matching the postgres deploy.
- **restart: unless-stopped** (survives NAS reboot) and a **healthcheck** against
  the management health endpoint (`/health/ready` on 9000 with
  `KC_HEALTH_ENABLED=true`) so "healthy" is a real signal and a Postgres-less boot
  fails fast rather than coming up half-configured.
- Commit `deploy/keycloak/.env.deploy.example` (the full env surface, all values
  blank) + a short `deploy/keycloak/README.md` pointer to the runbook. Add
  `deploy/keycloak/.env`, `.env.deploy`, and any `certs/` to `.gitignore`.

**Env-var surface** (name it fully so nothing leaks into git and the runbook can
render `.env`): `POSTGRES`/`KC_DB_PASSWORD`, `KC_BOOTSTRAP_ADMIN_USERNAME`,
`KC_BOOTSTRAP_ADMIN_PASSWORD`, `KC_HOSTNAME`, cert file paths, `KC_HTTPS_PORT`.

**Out of scope for this task (name negatively):** the `extra_hosts` tailnet-IP
JWKS entry is an **A2 server** concern on the `study_tutor_http` container, **not**
on this keycloak container — do not add it here. No `deploy.sh`/`smoke.sh` this
slice (runbook-driven; TASK-KC-005). No users, no secrets in any committed file.

## Acceptance Criteria

- [ ] `deploy/keycloak/docker-compose.yml` defines `study_tutor_keycloak` with a **pinned** `26.6.x` image (via Dockerfile FROM or `image:`), `mem_limit: 2g`, `restart: unless-stopped`, and a healthcheck; a floating tag (`:latest`, `:26`) is absent
- [ ] The start command is `start --optimized --import-realm`; the optimized build (`--db=postgres`) is baked (Dockerfile or equivalent) so `--optimized` is valid
- [ ] Compose mounts the tailscale cert + key and serves https on 8443; `KC_HOSTNAME` yields the pinned `whitestocks.tailebf801.ts.net:8443` issuer
- [ ] `KC_DB_URL` matches the §4 KEYCLOAK_DB contract exactly (`jdbc:postgresql://study_tutor_postgres:5432/keycloak`, intra-network 5432 not host 5434); realm dir mounts to `/opt/keycloak/data/import`
- [ ] Bootstrap admin comes only from env; `deploy/keycloak/.env.deploy.example` exists with all values blank; `.env`, `.env.deploy`, and cert material are gitignored (`git check-ignore` passes)
- [ ] No user, no client secret, and no admin credential appears in any committed file under `deploy/keycloak/`

## BDD Scenarios Served

- "The Keycloak identity service starts and reports healthy"
- "it should be the pinned Keycloak 26.6 image, not a floating tag"
- "The identity service starts across the supported memory sizing band"
- "A memory limit below the supported minimum starves the identity service"
- "A floating or mismatched image tag fails the version gate"
- "The identity service and its realm survive a NAS reboot"
- "The identity service fails fast when Postgres is unavailable at boot"

## Seam Tests

The following seam tests validate the §4 integration contracts this task consumes.
Prompt-output only — emit as `tests/seam/test_keycloak_compose_contract.py` if implemented.

```python
"""Seam test: verify KEYCLOAK_DB + REALM_IMPORT contracts in the compose artifact."""
import pathlib
import pytest
import yaml


@pytest.mark.seam
@pytest.mark.integration_contract("KEYCLOAK_DB")
def test_keycloak_db_url_matches_contract():
    """Contract: Keycloak connects to the co-located keycloak DB over the shared
    network at intra-container port 5432, DB name `keycloak`.
    Producer: TASK-KC-003; consumer: this task.
    """
    compose = yaml.safe_load(pathlib.Path("deploy/keycloak/docker-compose.yml").read_text())
    svc = compose["services"]["study_tutor_keycloak"]
    env = {**svc.get("environment", {})} if isinstance(svc.get("environment"), dict) else {}
    blob = str(svc.get("environment"))
    assert "jdbc:postgresql://study_tutor_postgres:5432/keycloak" in blob, \
        "KC_DB_URL must use intra-network 5432 and DB name keycloak, not host :5434"


@pytest.mark.seam
@pytest.mark.integration_contract("REALM_IMPORT")
def test_realm_import_mounted_and_enabled():
    """Contract: realm-as-code dir is mounted to the import path and --import-realm runs.
    Producer: TASK-KC-002; consumer: this task.
    """
    text = pathlib.Path("deploy/keycloak/docker-compose.yml").read_text()
    assert "/opt/keycloak/data/import" in text, "realm dir must mount to the import path"
    assert "--import-realm" in text, "start command must include --import-realm"
```

## References

- [ADR-ARCH-028](../../../docs/architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md) D1/D2 · design [KC-D1/D2](../../../docs/design/keycloak-auth-user-management-design.md) · postgres [docker-compose.yml](../../../deploy/postgres/docker-compose.yml) as the shape to mirror · IMPLEMENTATION-GUIDE §4 (KEYCLOAK_DB, REALM_IMPORT) · security-touching (identity infra) ⇒ FULL_REQUIRED human checkpoint regardless of score
