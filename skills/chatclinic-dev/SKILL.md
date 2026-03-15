---
name: chatclinic-dev
description: Use when developing the clinical multimodal workspace that follows the ChatGenome frontend concept but targets clinical tables and medical imaging rather than genomics VCF review.
---

# ChatClinic Dev

Use this skill when working on the `clinical_multimodal_workspace` repository.

## Purpose

This workspace is a sibling product to `ChatGenome`.

Reuse:

- the `Sources / Chat / Studio` shell
- grounded explanation patterns
- card-based Studio navigation

Do not reuse genomics-specific analysis logic.

## First files to inspect

- `README.md`
- `HANDOFF.md`
- `architecture.md`
- `app/main.py`
- `webapp/app/page.tsx`
- `webapp/app/globals.css`

## Development rule

Always keep the order:

1. deterministic parsing
2. deterministic QC and findings
3. Studio artifact generation
4. grounded chat explanation

The model should not infer clinical findings directly from raw tables or images.
