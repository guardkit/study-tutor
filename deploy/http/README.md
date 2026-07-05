# study-tutor HTTP Session API Deployment

**Independent deployment** for the HTTP session API (FEAT-APP-001 / ADR-ARCH-023).

This deployment is **independent** of the root `docker-compose.study-tutor.yml` (which requires NATS). The HTTP service runs standalone against the StudentStore (Postgres), no NATS coupling.

## Prerequisites

1. **StudentStore (Postgres) running** on port 5434 (see `deploy/postgres/`)
2. **Student identity rows seeded**:
   ```bash
   study-tutor seed-students
   ```
   This creates the required `student` rows for the configured tokens. Without it, authenticated requests fail with `Unauthenticated` (FK violation guard, ASSUM-001).

## Quick Start

1. Copy `.env.example` to `.env` and configure (see Flavours below)
2. Start the service:
   ```bash
   docker compose up -d
   ```
3. Health check:
   ```bash
   curl http://localhost:8100/healthz
   ```

## Flavours: Dev vs Prod

The deployment supports two **flavours** via environment variables. The compose file is identical; only the `.env` configuration differs.

### Dev Flavour

**Two tokens + reset endpoint enabled**

```bash
# .env for dev
STUDY_TUTOR_PG_DSN=postgresql://study_tutor:<password>@<host>:5434/study_tutor
STUDY_TUTOR_HTTP_TOKENS={"token-lilymay": "lilymay", "token-alex": "alex"}
STUDY_TUTOR_HTTP_DEV_RESET=1
```

With `STUDY_TUTOR_HTTP_DEV_RESET=1`, the `POST /__dev__/reset` endpoint is mounted (truncates session/turn rows for test isolation).

### Prod Flavour

**Single token, no reset endpoint**

```bash
# .env for prod
STUDY_TUTOR_PG_DSN=postgresql://study_tutor:<password>@<host>:5434/study_tutor
STUDY_TUTOR_HTTP_TOKENS={"token-lilymay": "lilymay"}
# STUDY_TUTOR_HTTP_DEV_RESET is NOT set — reset route does not exist
```

With `STUDY_TUTOR_HTTP_DEV_RESET` unset, `POST /__dev__/reset` returns 404 (unknown route).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STUDY_TUTOR_PG_DSN` | **Yes** | Postgres connection string (e.g., `postgresql://study_tutor:pass@host:5434/study_tutor`) |
| `STUDY_TUTOR_HTTP_TOKENS` | **Yes** | JSON object mapping Bearer tokens to student IDs (e.g., `{"token-lilymay": "lilymay"}`) |
| `STUDY_TUTOR_HTTP_DEV_RESET` | No | Dev-only flag (`1` to enable reset endpoint; unset for prod) |
| `HTTP_PORT` | No | Host-side port mapping (default: `8100`) |

## Service Details

- **Port:** 8100
- **Healthcheck:** `GET /healthz` (READY semantics from TASK-APP1-04)
- **API Endpoints:** See `docs/design/contracts/API-session-http-binding.md`
- **Auth:** `Authorization: Bearer <token>` (header-only, server-resolved student_id)

## Token Values

**Dev tokens** (per `API-session-http-binding.md` §5.1):

| Token | student_id |
|-------|------------|
| `token-lilymay` | `lilymay` |
| `token-alex` | `alex` |

**Prod:** Use `token-lilymay` only (or a production-appropriate token for the deployed student).

## Maintenance

**Logs:**
```bash
docker compose logs -f study_tutor_http
```

**Restart:**
```bash
docker compose restart study_tutor_http
```

**Stop:**
```bash
docker compose down
```

## Notes

- **Independent deployment:** This HTTP service runs standalone against Postgres. No NATS infrastructure or credentials required (ADR-ARCH-023 independent-deployability posture).
- **Seed before use:** Run `study-tutor seed-students` before starting the service to avoid FK violation errors.
- **Test isolation:** Dev reset (`POST /__dev__/reset`) truncates sessions but preserves learner state (XP, streaks, confidence).
