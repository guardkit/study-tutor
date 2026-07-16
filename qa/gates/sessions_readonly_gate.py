#!/usr/bin/env python3
"""F4 SESSIONS-READONLY gate — the bearer-authed read surface.

Registered in qa/gates/registry.yaml as gate id ``sessions-readonly``. Drives the
LIVE study-tutor serve-http deployment and proves the auth surface is gated
WITHOUT embedding any secret:

  POSITIVE: GET /api/sessions with Authorization: Bearer <STUDY_TUTOR_GATE_TOKEN>
            -> 200 and a JSON ARRAY body (list_sessions projects the caller's
            sessions to a list, src/study_tutor/http/app.py:191; the array is
            empty for a freshly-seeded student, which is still a valid 200 shape).
  NEGATIVE: the SAME GET with NO Authorization header -> 401 (the transport maps
            Unauthenticated to HTTP 401 with error_type "Unauthenticated",
            app.py:75; verified live 2026-07-16).

The bearer token is read from the env var named by ``auth_token_env``
(STUDY_TUTOR_GATE_TOKEN). If that env var is UNSET the gate FAILS LOUD (via
_gatelib.auth_headers) — never a silent skip; the token value is never written
to a script, spec, or the evidence file.

F4 contract via _gatelib: exit 0 = pass; non-zero enumerates failures in the JSON
results envelope. Base URL from $STUDY_TUTOR_BASE_URL (default http://localhost:8110).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _gatelib  # noqa: E402

GATE_ID = "sessions-readonly"

SPEC = {
    "gate_id": GATE_ID,
    "base_url_env": "STUDY_TUTOR_BASE_URL",
    "default_base_url": "http://localhost:8110",
    "auth_token_env": "STUDY_TUTOR_GATE_TOKEN",
}


def main() -> None:
    base = (os.environ.get("STUDY_TUTOR_BASE_URL") or "http://localhost:8110").rstrip("/")
    url = base + "/api/sessions"
    assertions: List[Dict[str, Any]] = []

    # Resolve the bearer header. An unset auth_token_env is a loud failure, not
    # a skip — and no token value ever appears in the assertion or evidence.
    headers, auth_err = _gatelib.auth_headers(SPEC)
    if auth_err is not None:
        _gatelib._emit_and_exit([auth_err])

    # Positive: authed GET.
    a_status, a_headers, a_body, a_err = _gatelib.http_get(url, headers=headers)
    # Negative: same GET with NO Authorization header.
    n_status, n_headers, n_body, n_err = _gatelib.http_get(url, headers=None)

    evidence = _gatelib._write_evidence(GATE_ID, {
        "url": url,
        "authed": {"status": a_status, "headers": a_headers,
                   "body": a_body, "error": str(a_err) if a_err else None},
        "anonymous": {"status": n_status, "headers": n_headers,
                      "body": n_body, "error": str(n_err) if n_err else None},
    })

    if a_err is not None:
        assertions.append({
            "id": f"{GATE_ID}::reachable", "status": "fail",
            "observed": f"request error: {a_err}",
            "expected": f"HTTP 200 from {url}", "evidence_ref": evidence,
        })
        _gatelib._emit_and_exit(assertions)

    # Positive assertions.
    assertions.append({
        "id": f"{GATE_ID}::authed_status",
        "status": "pass" if a_status == 200 else "fail",
        "observed": str(a_status), "expected": "200 with a valid bearer token",
        "evidence_ref": evidence,
    })

    try:
        parsed = json.loads(a_body)
    except Exception:
        parsed = None
    list_ok = isinstance(parsed, list)
    assertions.append({
        "id": f"{GATE_ID}::authed_body_list",
        "status": "pass" if list_ok else "fail",
        "observed": type(parsed).__name__ if parsed is not None else "body not JSON",
        "expected": "JSON array body (contract §5.2 — list of session summaries)",
        "evidence_ref": evidence,
    })

    # Negative assertion — the auth surface refuses the anonymous caller.
    anon_ok = n_status in (401, 403)
    assertions.append({
        "id": f"{GATE_ID}::anonymous_refused",
        "status": "pass" if anon_ok else "fail",
        "observed": str(n_status),
        "expected": "401/403 (no Authorization header => Unauthenticated -> 401)",
        "evidence_ref": evidence,
    })

    _gatelib._emit_and_exit(assertions)


if __name__ == "__main__":
    main()
