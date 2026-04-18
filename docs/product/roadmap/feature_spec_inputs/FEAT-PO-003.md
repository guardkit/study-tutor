# Bring-your-own-sources public repo packaging

## Description

Package the tutor as an open-source methodology rather than an open-source dataset by separating clean pipeline code from private curriculum materials, ChromaDB collections, training data, and fine-tuned weights. The repository must explain how a user can supply licensed study materials into the ingestion pipeline, while making it explicit which assets stay private for copyright and hackathon compliance reasons.

## Bounded Context

Submission Packaging BC

## Source Documents

- copyright-training-data-analysis.md
- gemma4-hackathon-submission-plan.md

## Constraints

- Must not publish Mr Bruff PDFs, AQA materials, train.jsonl, ChromaDB collections, or private adapters
- Must support hackathon requirement for a public repository
- Must document provenance and compliance posture transparently

## Dependencies

- FEAT-PO-001

## Suggested Context Files

- README.md
- domains/gcse-english/sources/README.md
- docs/adr/
- LICENSE
