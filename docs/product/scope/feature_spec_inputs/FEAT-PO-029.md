# Tool Selection for Eligible Tasks

## Description

The assistant selects a documented tool path when the current task requires external capability that is available in the product's tool set. The selection behaviour distinguishes between tasks that can be completed directly in conversation and tasks that should use an explicitly supported tool route.

## Bounded Context

Tool Use

## Source Documents

- tool-selection.md
- tool-catalog.md

## Constraints

- Must only select from documented tools
- Must preserve direct conversational handling for tasks that do not require a tool

## Dependencies

- FEAT-PO-026
- FEAT-PO-017

## Suggested Context Files

- docs/tool-selection.md
- docs/tool-catalog.md
