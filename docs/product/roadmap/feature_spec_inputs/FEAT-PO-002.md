# Fine-tuned English tutoring runtime over local deployment

## Description

Wrap the existing Gemma 4 31B fine-tuned tutoring behaviour in a stable local runtime that Lilymay can use consistently through the current Ollama-based path while preserving the option to migrate to vLLM later. The runtime must support key GCSE English interactions such as asking analytical questions, receiving scaffolded essay feedback, and practising exam responses in language appropriate for a Year 10 student.

## Bounded Context

Tutoring Runtime BC

## Source Documents

- gemma4-hackathon-submission-plan.md
- copyright-training-data-analysis.md

## Constraints

- Must remain on-device/offline-friendly
- Must use existing private model assets without publishing weights
- Must work with the current basic version already used via Ollama

## Dependencies

- FEAT-PO-001

## Suggested Context Files

- src/runtime/
- src/interfaces/cli.py
- src/interfaces/api.py
- README.md
