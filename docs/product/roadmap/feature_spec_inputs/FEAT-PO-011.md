# Tutor AgentManifest and multi-interface capability declaration

## Description

Define a single manifest for the tutor agent that declares supported subjects, interfaces, dependencies, and capabilities such as tutoring, quiz generation, essay feedback, and progress reporting. This gives the product a stable contract for Open WebUI today, custom web UI next, and future voice or fleet integration later without refactoring the tutor's identity each time transport or interface changes.

## Bounded Context

Agent Capability BC

## Source Documents

- deepagents-patterns-review.md

## Constraints

- Must be the source of truth for capability exposure
- Must cover English immediately and planned subjects explicitly
- Must support future custom web UI and Reachy/voice adapters

## Dependencies

- FEAT-PO-002
- FEAT-PO-010

## Suggested Context Files

- src/config/agent_manifest.py
- src/config/tutor_config.yaml
- docs/adr/
