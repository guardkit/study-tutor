# Reference Implementation — Keycloak JWT validation (from lpa-platform-poc)

**Purpose:** de-risk **FEAT-AUTH-002** (design [KC-D6](../keycloak-auth-user-management-design.md))
by pointing spec + build at *working, in-production-adjacent* code. The FinProxy LPA POC
(`../../../lpa-platform-poc`) has run Keycloak-fronted OIDC since 2026-05; the pieces below are
proven and transfer almost directly. This note also flags where study-tutor **deliberately diverges**,
so the reference is copied with eyes open — not cargo-culted.

**Source commit basis:** read 2026-07-08 from
`lpa-platform-poc/{docker-compose.poc.yml, src/auth.py, src/config.py, keycloak/finproxy-realm.json}`.

---

## 1. What transfers directly (copy the shape)

### 1a. The issuer-vs-internal-URL split — solves the KC-D2 "known gotcha"
The POC keeps **two** Keycloak base URLs and this is the single most valuable thing to lift:

- `keycloak_url` (internal, `http://keycloak:8180`) — used for **JWKS fetch** and token endpoint
  (server-to-server, inside the docker network).
- `keycloak_public_url` (browser-facing) — used as the **validated `issuer`** and for authorize/logout.

```python
# lpa-platform-poc/src/config.py  (proven)
@property
def issuer(self) -> str:
    # KC_HOSTNAME_STRICT=false → Keycloak issues `iss` matching the host the
    # ORIGINAL auth request hit. Browser hits the PUBLIC url, so the token's iss
    # is the public url even though the API exchanged the code internally.
    return f"{self.keycloak_public_url}/realms/{self.keycloak_realm}"

@property
def jwks_url(self) -> str:                       # internal host — NOT the issuer host
    return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"
```

**Study-tutor mapping (KC-D2):** identical principle, one topology difference — in the POC the
server and Keycloak are **co-located** in one compose network, so JWKS-over-service-name "just works."
In study-tutor the server (**GB10**) and Keycloak (**NAS**) are on **different hosts**, so the JWKS
fetch crosses the tailnet. That is exactly why the design has:
- `STUDY_TUTOR_OIDC_ISSUER` pinned to the **ts.net name** (`https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`), and
- `STUDY_TUTOR_OIDC_JWKS_URL` **override** so the fetch can go via the tailnet IP
  (`extra_hosts: whitestocks.tailebf801.ts.net:100.92.74.2`) while `iss` validation stays pinned to the name.

The POC proves the split works; study-tutor just moves the JWKS leg from a service name to a
tailnet-IP `extra_hosts` entry (same mechanism the POC already uses for the GB10 llama-swap host).

### 1b. Cached-JWKS + validate — the core of `KeycloakTokenResolver`
```python
# lpa-platform-poc/src/auth.py  (proven; python-jose)
_jwks_cache = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 300

async def validate_token(token: str) -> dict[str, Any]:
    jwks = await _get_jwks()                              # 300s TTL cache
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(401, "Unknown key id")
    return jwt.decode(
        token, key,
        algorithms=[header.get("alg", "RS256")],
        issuer=settings.issuer,                          # iss checked against PUBLIC url
        options={"verify_aud": False, "verify_at_hash": False},
    )
```
This is functionally `KeycloakTokenResolver.resolve()` minus the `student_id` extraction. The manual
`kid` lookup + TTL cache is precisely what **`PyJWKClient` automates** — see §2a.

---

## 2. Where study-tutor deliberately diverges (do NOT copy)

| Concern | POC (working) | study-tutor (KC-D#) | Why the difference |
|---|---|---|---|
| **JWT lib** | `python-jose`, hand-rolled JWKS cache | **PyJWT + `PyJWKClient`** (KC-D6) | PyJWKClient gives kid-rotation-aware caching for free; the manual cache in §1b is what it replaces. |
| **Auth model** | session/BFF: `request.session['user_sub']`, `get_current_user` reads a cookie | **stateless bearer** resolver behind `TokenResolver` (KC-D6) | study-tutor is a mobile/robot API, not a server-rendered web app — no server session, token validated per-request. |
| **Identity mapping** | `keycloak_sub` **column** on `users` + upsert/self-heal | **`student_id` user attribute → claim**, validated, then existing unseeded guard; **no column, no upsert** (KC-D3) | KC-D3 explicitly rejects the column: keeps the server stateless about mapping, no schema migration, single-student scope. |
| **`aud` check** | `verify_aud=False` | **verify `aud`** (KC-D6) | POC skipped audience; study-tutor validates iss **and** aud. |
| **Users in realm JSON** | test donors/attorneys **committed** to `finproxy-realm.json` | users **runbook-created, never in git** (KC-D3) | study-tutor stores a **minor's** identity — PII posture forbids committing users; only realm/clients/roles/mappers go in `deploy/keycloak/realm/`. |
| **Client type** | one **confidential** web client, no PKCE | **public PKCE-S256** app + **device-grant** robot (KC-D4) | Neither mobile flow is exercised by the POC — genuinely new surface. |

### 2a. Same logic, PyJWT form (the shape FEAT-AUTH-002 actually builds)
```python
# http/auth_keycloak.py  (target — PyJWT, not jose)
from jwt import PyJWKClient
import jwt

class KeycloakTokenResolver:                 # implements TokenResolver
    def __init__(self, jwks_url: str, issuer: str, audience: str, student_claim: str):
        self._jwks = PyJWKClient(jwks_url)   # cached, kid-rotation aware (replaces §1b cache)
        self._issuer, self._audience, self._claim = issuer, audience, student_claim

    async def resolve(self, token: str) -> str:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token, signing_key.key, algorithms=["RS256"],
                issuer=self._issuer, audience=self._audience,   # iss AND aud (vs POC)
            )
        except jwt.PyJWTError as exc:
            raise Unauthenticated(str(exc)) from exc
        student_id = claims.get(self._claim)                    # KC-D3 attribute→claim
        if not student_id:
            raise Unauthenticated("token missing student_id claim")
        return student_id                                       # unseeded guard still runs upstream
```

---

## 3. Proven mechanisms the POC also demonstrates (evidence, not code to copy)

- **Attribute → claim protocol mapper** (KC-D3's mechanism): POC attorney users carry a `birthdate`
  attribute that arrives as a claim and is parsed server-side. Same mapper mechanism `student_id` uses.
- **`extra_hosts` for container-can't-resolve-MagicDNS** (KC-D2 gotcha): POC pins the GB10 host
  (`promaxgb10-41b1:100.84.90.91`) on the api container — study-tutor pins the NAS the same way.
- **Realm-as-code import** via `--import-realm` with **pinned `id` fields** (prevents sub-drift across
  `down/up` cycles). study-tutor keeps the pinning for realm/clients/roles; users stay out of git.

## 4. What the POC does NOT prove (still on the §5 ratification / gates)

- **NAS placement + DSM `tailscale cert` https issuer** (KC-D1/D2) — POC runs on **GB10**, `start-dev`,
  `sslRequired: none`, **http** issuer. The https/DSM-cert path is untested here → this is the live
  risk `/arch-refine` (ADR-ARCH-028) covers.
- **Public PKCE-S256 app flow** and **device-authorization-grant robot flow** (KC-D4) — the POC's
  single confidential web client exercises neither.

---

*Companion to [keycloak-auth-user-management-design.md](../keycloak-auth-user-management-design.md)
(KC-D2/D3/D6). Written 2026-07-08 from the working lpa-platform-poc stack.*
