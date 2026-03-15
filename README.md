# ChatClinic

Interactive workspace scaffold for clinical tabular data and medical imaging review.

This project is the recommended next-step sibling of `ChatGenome`:

- keep the same high-level `Sources / Chat / Studio` product concept
- reuse grounded-chat and Studio-card ideas
- replace genomics-specific services with clinical data and imaging pipelines
- keep domain logic separated from `ChatGenome`

## Why this is a separate project

Do not continue by copying all of `ChatGenome` and editing in place.

Use a new project when:

- the domain changes from genomics VCF review to clinical data and imaging
- different datasets, privacy rules, and workflows apply
- you want to preserve `ChatGenome` as a stable genomics product

## Initial structure

```text
clinical_multimodal_workspace/
  README.md
  CONTRIBUTING.md
  HANDOFF.md
  architecture.md
  .env.example
  .gitignore
  app/
    main.py
    services/
  webapp/
    package.json
    tsconfig.json
    next.config.mjs
    app/
      layout.tsx
      page.tsx
      globals.css
  skills/
    chatclinic-dev/
      SKILL.md
```

## Reuse from ChatGenome

Safe to reuse:

- 3-column workspace pattern
- chat panel concept
- Studio card concept
- environment variable pattern
- contributor and handoff docs
- grounded explanation workflow

Do not directly reuse as-is:

- VCF upload logic
- `pysam`, IGV, ClinVar, ROH, VEP, SnpEff, gnomAD code
- genomics-specific Studio cards

## Suggested next build order

1. Define supported inputs:
   - clinical tables
   - CSV/TSV/Excel
   - DICOM or image series
2. Build deterministic parsing and QC first
3. Add grounded summary generation second
4. Add Studio cards for modality-specific review
5. Add follow-up chat only after the deterministic outputs exist

## Quick start

```bash
cd /Users/jongcye/Documents/Codex/workspace/clinical_multimodal_workspace
cp .env.example .env
```

Then set:

```bash
OPENAI_API_KEY=sk-...
OPENAI_WORKFLOW_MODEL=gpt-5-nano
OPENAI_MODEL=gpt-5-mini
```

## Relationship to ChatGenome

`ChatGenome` remains the genomics product.

This workspace is the starting point for a broader clinical and imaging platform with a similar frontend concept but a different backend domain model.
