#!/usr/bin/env python3
"""F4 FEATURE-BEHAVIOUR gate TEMPLATE — parameterized by endpoint + assertions.

Every later study-tutor feature INSTANTIATES this template rather than editing it:

    cp qa/gates/feature_behaviour_gate.py qa/gates/<feature>_gate.py
    # edit the SPEC block below: request.path, expect_status, headers_present,
    # json_assertions (each: {"id", "path", and one of "equals" / "type":"int" /
    # "exists": true}); add "auth_token_env": "STUDY_TUTOR_GATE_TOKEN" for a
    # bearer-authed endpoint (an authed spec with that env UNSET fails loud — it
    # never skips, and no token value is ever embedded here).
    # then register it in qa/gates/registry.yaml as a new gate entry pointing at
    # qa/gates/<feature>_gate.py with its own pass-bar-<TASK>.yaml.

For an ad-hoc run you may instead point $FEATURE_GATE_SPEC at a JSON file
carrying the SPEC. The gate honours the F4 contract via _gatelib (exit 0 = pass;
non-zero enumerates failing assertions as the JSON results envelope). Target
base URL comes from $STUDY_TUTOR_BASE_URL (default http://localhost:8110).

Example instantiation for a hypothetical authed GET /api/foo -> JSON {items:[…]}:

    SPEC = {
        "gate_id": "foo",
        "base_url_env": "STUDY_TUTOR_BASE_URL",
        "default_base_url": "http://localhost:8110",
        "auth_token_env": "STUDY_TUTOR_GATE_TOKEN",
        "request": {"method": "GET", "path": "/api/foo"},
        "expect_status": 200,
        "json_assertions": [
            {"id": "foo::items_present", "path": "items", "exists": True},
        ],
    }
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _gatelib  # noqa: E402

# --- EDIT THIS BLOCK WHEN INSTANTIATING -----------------------------------
SPEC = {
    "gate_id": "feature-behaviour",
    "base_url_env": "STUDY_TUTOR_BASE_URL",
    "default_base_url": "http://localhost:8110",
    # "auth_token_env": "STUDY_TUTOR_GATE_TOKEN",  # uncomment for a bearer-authed endpoint
    "request": {"method": "GET", "path": "/REPLACE_ME"},
    "expect_status": 200,
    "headers_present": [],
    "json_assertions": [
        # {"id": "feature::field_present", "path": "some_field", "exists": True},
        # {"id": "feature::field_value",   "path": "some_field", "equals": "expected"},
        # {"id": "feature::count_is_int",  "path": "count",      "type": "int"},
    ],
}
# --------------------------------------------------------------------------

if __name__ == "__main__":
    override = os.environ.get("FEATURE_GATE_SPEC")
    spec = json.loads(open(override, encoding="utf-8").read()) if override else SPEC
    if spec["request"]["path"] == "/REPLACE_ME":
        # Honest "template not instantiated" — never a vacuous green.
        print(json.dumps({"assertions": [{
            "id": "feature-behaviour::not_instantiated",
            "status": "fail",
            "observed": "request.path is the unedited placeholder /REPLACE_ME",
            "expected": "instantiate the SPEC (endpoint + assertions) before registering this gate",
        }]}))
        sys.exit(1)
    _gatelib.run_spec(spec)
