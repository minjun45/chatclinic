# Contributing

## Project goal

Build a clinical and medical-imaging review workspace that keeps the ChatGenome product feel while remaining a separate codebase.

## Ground rules

- keep deterministic analysis ahead of LLM explanation
- avoid mixing genomics-only code into this repo
- keep `.env` local
- use `.env.example` as the template
- keep Studio cards aligned with backend-produced artifacts

## First development steps

1. Define data modalities to support
2. Add deterministic parsers
3. Add modality-specific QC
4. Add Studio cards
5. Add grounded chat

## Validation

- backend: simple FastAPI health checks and parser smoke tests
- frontend: TypeScript checks and visual verification
- do not claim clinical interpretation from raw data without deterministic evidence
