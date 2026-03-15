# Architecture

## Product shape

Three-column `ChatClinic` workspace:

- `Sources`
  input files, dataset selection, run state
- `Chat`
  intake questions, grounded summary, continued dialogue
- `Studio`
  structured result cards and modality-specific views

## Backend

- `FastAPI`
- deterministic services under `app/services/`
- future modules:
  - `clinical_tables.py`
  - `imaging_series.py`
  - `reporting.py`

## Frontend

- `Next.js`
- one shared shell
- Studio cards switch detailed views without leaving the workspace

## Key design rule

Never let the model invent findings from raw medical data.

Required order:

1. parse data
2. compute deterministic artifacts
3. summarize those artifacts
4. let the model explain the artifacts
