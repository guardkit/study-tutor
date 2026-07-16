"""Shared engine for study-tutor F4 gate scripts.

Ported from api_test/qa/gates/_gatelib.py — VERBATIM in behaviour, adapted only
where the venue is named (base-url env var STUDY_TUTOR_BASE_URL, default
http://localhost:8110, evidence under qa/gates/evidence/) plus ONE additive
capability this venue needs (bearer auth — see below).

Implements the F4 gate-script CONTRACT
(guardkit/qa/formats/gate_registry.py): a gate prints a JSON object carrying an
``assertions`` list on stdout — each assertion ``{id, status, observed,
expected, evidence_ref}`` — and exits 0 iff every assertion passed; a non-zero
exit MUST enumerate its failing assertions. The live-gate executor parses that
envelope verbatim.

stdlib only (urllib) so a gate runs against the live deployment with no extra
dependencies. A gate is driven by a SPEC dict:

    {
      "gate_id": "healthz",
      "base_url_env": "STUDY_TUTOR_BASE_URL",   # env-var NAME (LPA-02), not a URL
      "default_base_url": "http://localhost:8110",
      "request": {"method": "GET", "path": "/healthz"},
      "expect_status": 200,
      "headers_present": ["x-correlation-id"],
      "json_assertions": [
        {"id": "healthz::status_ok", "path": "status", "equals": "ok"},
        {"id": "stat::count_is_int", "path": "count",  "type": "int"},
        {"id": "stat::field_present","path": "service","exists": true},
      ],
    }

ADDITIVE CAPABILITY — bearer auth (study-tutor exposes a bearer-authed API):
a SPEC may name an env var in ``auth_token_env``. When set, every HTTP call the
gate makes sends ``Authorization: Bearer <value-of-that-env>``. If the named env
var is UNSET, the gate FAILS LOUD with a single assertion (never a silent skip);
the token VALUE is never embedded in a spec, a script, or the evidence file.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EVIDENCE_DIR = Path("qa/gates/evidence")


def http_get(
    url: str,
    timeout: float = 15.0,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[int], Dict[str, str], str, Optional[Exception]]:
    """GET ``url`` with stdlib. Returns (status, lowercased-headers, body, error)."""
    req = urllib.request.Request(url, method="GET", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, resp_headers, body, None
    except urllib.error.HTTPError as exc:  # a real HTTP response (4xx/5xx)
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        resp_headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, resp_headers, body, None
    except Exception as exc:  # connection refused / DNS / timeout — not reachable
        return None, {}, "", exc


def http_post(
    url: str,
    timeout: float = 15.0,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[int], Dict[str, str], str, Optional[Exception]]:
    """POST an empty JSON body to ``url`` with stdlib. Same return shape as http_get.

    Used by negative-path assertions (e.g. method-not-allowed on a GET-only route).
    """
    send_headers = {"Content-Type": "application/json"}
    if headers:
        send_headers.update(headers)
    req = urllib.request.Request(url, data=b"{}", method="POST", headers=send_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, resp_headers, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        resp_headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, resp_headers, body, None
    except Exception as exc:
        return None, {}, "", exc


def _base_url(spec: Dict[str, Any]) -> str:
    env_name = spec.get("base_url_env", "STUDY_TUTOR_BASE_URL")
    url = os.environ.get(env_name) or spec.get("default_base_url", "http://localhost:8110")
    return url.rstrip("/")


def auth_headers(spec: Dict[str, Any]) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
    """Resolve the bearer header for a SPEC's ``auth_token_env``.

    Returns ``(headers, error_assertion)``:
    - no ``auth_token_env`` on the spec  => ``({}, None)`` (an unauthed call)
    - env var set                        => ``({"Authorization": "Bearer …"}, None)``
    - env var named but UNSET            => ``(None, <fail-loud assertion>)``

    The token VALUE is never returned in the assertion nor written to evidence —
    only the NAME of the missing env var is surfaced.
    """
    env_name = spec.get("auth_token_env")
    if not env_name:
        return {}, None
    token = os.environ.get(env_name)
    if not token:
        return None, {
            "id": f"{spec['gate_id']}::auth_token_present",
            "status": "fail",
            "observed": f"env var {env_name} is unset",
            "expected": f"env var {env_name} set to the bearer token for the authed call",
        }
    return {"Authorization": f"Bearer {token}"}, None


def _write_evidence(gate_id: str, payload: Dict[str, Any]) -> Optional[str]:
    try:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        path = EVIDENCE_DIR / f"{gate_id}_latest.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)
    except Exception:
        return None


def _emit_and_exit(assertions: List[Dict[str, Any]]) -> None:
    print(json.dumps({"assertions": assertions}))
    sys.exit(0 if all(a["status"] == "pass" for a in assertions) else 1)


def run_spec(spec: Dict[str, Any]) -> None:
    """Execute a gate SPEC against the live target and emit the F4 envelope."""
    gate_id = spec["gate_id"]
    url = _base_url(spec) + spec["request"]["path"]

    # Additive: resolve bearer auth. An authed spec with the env var UNSET fails
    # loud here — never a silent skip, never a token value on the wire log.
    headers, auth_err = auth_headers(spec)
    if auth_err is not None:
        _emit_and_exit([auth_err])

    status, resp_headers, body, err = http_get(url, spec.get("timeout", 15.0), headers)
    evidence = _write_evidence(
        gate_id,
        {"url": url, "authed": bool(headers), "status": status,
         "headers": resp_headers, "body": body,
         "error": str(err) if err else None},
    )
    assertions: List[Dict[str, Any]] = []

    # Not reachable at all => single honest failure (exit 1). Environment
    # attribution is pre-flight/F16's job; the gate reports the observed red.
    if err is not None:
        assertions.append({
            "id": f"{gate_id}::reachable",
            "status": "fail",
            "observed": f"request error: {err}",
            "expected": f"HTTP {spec.get('expect_status', 200)} from {url}",
            "evidence_ref": evidence,
        })
        _emit_and_exit(assertions)

    expect_status = spec.get("expect_status", 200)
    assertions.append({
        "id": f"{gate_id}::status",
        "status": "pass" if status == expect_status else "fail",
        "observed": str(status),
        "expected": str(expect_status),
        "evidence_ref": evidence,
    })

    for header in spec.get("headers_present", []):
        present = header.lower() in resp_headers
        assertions.append({
            "id": f"{gate_id}::header::{header.lower()}",
            "status": "pass" if present else "fail",
            "observed": "present" if present else "absent",
            "expected": f"response header {header} present",
            "evidence_ref": evidence,
        })

    json_assertions = spec.get("json_assertions", [])
    parsed: Any = None
    if json_assertions:
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = None

    for ja in json_assertions:
        key = ja["path"]
        observed = parsed.get(key) if isinstance(parsed, dict) else None
        if "equals" in ja:
            ok = observed == ja["equals"]
            expected = f"{key} == {ja['equals']!r}"
        elif ja.get("type") == "int":
            ok = isinstance(observed, int) and not isinstance(observed, bool)
            expected = f"{key} is an integer"
        else:  # exists (default)
            ok = isinstance(parsed, dict) and key in parsed
            expected = f"{key} present in JSON body"
        assertions.append({
            "id": ja["id"],
            "status": "pass" if ok else "fail",
            "observed": repr(observed) if isinstance(parsed, dict) else "body not JSON",
            "expected": expected,
            "evidence_ref": evidence,
        })

    _emit_and_exit(assertions)
