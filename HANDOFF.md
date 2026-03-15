# Handoff Notes

## What this workspace is

This is a clean starting scaffold for the `ChatClinic` clinical-data and medical-imaging review platform.

It is intentionally separate from `ChatGenome`.

## Shared concepts from ChatGenome

- `Sources / Chat / Studio` layout
- grounded explanation after deterministic processing
- card-based Studio exploration
- contributor and handoff documentation

## What still needs to be built

- clinical table ingestion
- DICOM/image ingestion
- modality-specific QC
- deterministic findings extraction
- Studio cards for imaging and clinical review
- secure storage and access controls

## Recommended next work

1. Add upload handlers for CSV/XLSX and DICOM
2. Define backend response models for clinical summary
3. Create Studio cards for:
   - data QC
   - cohort overview
   - imaging series review
   - report generation
4. Add grounded chat based on those deterministic artifacts
