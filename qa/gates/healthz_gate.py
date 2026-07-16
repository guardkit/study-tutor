#!/usr/bin/env python3
"""F4 HEALTHZ gate — GET /healthz 200 + JSON + status=="ok"; POST /healthz rejected.

Registered in qa/gates/registry.yaml as gate id ``healthz``. Drives the LIVE
study-tutor serve-http deployment: the READY health check (src/study_tutor/http/
app.py healthz, TASK-APP1-04) is an UNAUTHED route returning {"status": "ok"} at
200. The negative is the method-not-allowed path on the same route — /healthz is
mounted GET-only (Route(..., methods=["GET"])), so Starlette rejects POST with
405 (verified live 2026-07-16).

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

GATE_ID = "healthz"


def main() -> None:
    base = (os.environ.get("STUDY_TUTOR_BASE_URL") or "http://localhost:8110").rstrip("/")
    url = base + "/healthz"
    assertions: List[Dict[str, Any]] = []

    status, headers, body, err = _gatelib.http_get(url)
    post_status, _ph, post_body, post_err = _gatelib.http_post(url)
    evidence = _gatelib._write_evidence(GATE_ID, {
        "url": url,
        "get": {"status": status, "headers": headers, "body": body,
                "error": str(err) if err else None},
        "post": {"status": post_status, "body": post_body,
                 "error": str(post_err) if post_err else None},
    })

    if err is not None:
        assertions.append({
            "id": f"{GATE_ID}::reachable", "status": "fail",
            "observed": f"request error: {err}",
            "expected": f"HTTP 200 from {url}", "evidence_ref": evidence,
        })
        _gatelib._emit_and_exit(assertions)

    assertions.append({
        "id": f"{GATE_ID}::status", "status": "pass" if status == 200 else "fail",
        "observed": str(status), "expected": "200", "evidence_ref": evidence,
    })

    try:
        parsed = json.loads(body)
    except Exception:
        parsed = None
    body_ok = isinstance(parsed, dict)
    assertions.append({
        "id": f"{GATE_ID}::body_json", "status": "pass" if body_ok else "fail",
        "observed": "JSON object" if body_ok else "body not a JSON object",
        "expected": "JSON object body", "evidence_ref": evidence,
    })

    status_ok = body_ok and parsed.get("status") == "ok"
    assertions.append({
        "id": f"{GATE_ID}::status_ok", "status": "pass" if status_ok else "fail",
        "observed": repr(parsed.get("status")) if body_ok else "body not JSON",
        "expected": 'status == "ok"', "evidence_ref": evidence,
    })

    # Negative path — /healthz is GET-only, so POST is method-not-allowed (405).
    post_ok = post_status == 405
    assertions.append({
        "id": f"{GATE_ID}::post_method_not_allowed",
        "status": "pass" if post_ok else "fail",
        "observed": str(post_status),
        "expected": "405 (route mounted GET-only; POST is method-not-allowed)",
        "evidence_ref": evidence,
    })

    _gatelib._emit_and_exit(assertions)


if __name__ == "__main__":
    main()
