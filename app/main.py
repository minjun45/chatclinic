from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    import pydicom  # type: ignore
except Exception:  # pragma: no cover
    pydicom = None


class UploadedSourceSummary(BaseModel):
    file_name: str
    file_type: str
    modality: str
    size_bytes: int
    status: str


class IntakeSummaryResponse(BaseModel):
    source: UploadedSourceSummary
    grounded_summary: str
    studio_cards: list[dict[str, Any]]
    artifacts: dict[str, Any]


app = FastAPI(title="ChatClinic")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3010", "http://localhost:3010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _guess_modality(filename: str) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return "clinical-table", suffix.lstrip(".")
    if suffix in {".dcm", ".dicom"}:
        return "medical-image", suffix.lstrip(".")
    return "unknown", suffix.lstrip(".") or "unknown"


def _summarize_table(file_name: str, raw: bytes, suffix: str) -> IntakeSummaryResponse:
    delimiter = "\t" if suffix == "tsv" else ","
    decoded = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)
    rows = list(reader)
    columns = reader.fieldnames or []
    missing_cells = 0
    for row in rows:
        missing_cells += sum(1 for value in row.values() if value is None or str(value).strip() == "")
    missing_rate = (missing_cells / (max(len(rows), 1) * max(len(columns), 1))) if columns else 0.0

    summary = (
        f"This clinical table contains {len(rows)} row(s) and {len(columns)} column(s). "
        f"The detected schema includes {', '.join(columns[:8]) if columns else 'no readable columns'}. "
        f"Current table completeness is approximately {(1 - missing_rate) * 100:.1f}% based on non-empty cells. "
        "This first-pass summary is deterministic and should be followed by field-level validation, cohort profiling, and outcome-specific review."
    )

    studio_cards = [
        {"id": "qc", "title": "Clinical QC", "subtitle": "Rows, columns, completeness"},
        {"id": "schema", "title": "Schema Review", "subtitle": "Detected variables and types"},
        {"id": "cohort", "title": "Cohort Summary", "subtitle": "Record counts and distributions"},
        {"id": "report", "title": "Report Draft", "subtitle": "Grounded narrative summary"},
    ]
    artifacts = {
        "qc": {
            "row_count": len(rows),
            "column_count": len(columns),
            "missing_rate": missing_rate,
        },
        "schema": {
            "columns": columns,
            "sample_rows": rows[:3],
        },
        "cohort": {
            "record_count": len(rows),
            "available_fields": len(columns),
        },
        "report": {
            "draft": summary,
        },
    }
    return IntakeSummaryResponse(
        source=UploadedSourceSummary(
            file_name=file_name,
            file_type=suffix,
            modality="clinical-table",
            size_bytes=len(raw),
            status="parsed",
        ),
        grounded_summary=summary,
        studio_cards=studio_cards,
        artifacts=artifacts,
    )


def _summarize_dicom(file_name: str, raw: bytes, suffix: str) -> IntakeSummaryResponse:
    meta: dict[str, Any] = {
        "patient_id": "not available",
        "study_description": "not available",
        "modality": "not available",
        "rows": "not available",
        "columns": "not available",
    }
    if pydicom is not None:
        try:
            dataset = pydicom.dcmread(io.BytesIO(raw), stop_before_pixels=True, force=True)
            meta = {
                "patient_id": str(getattr(dataset, "PatientID", "not available")),
                "study_description": str(getattr(dataset, "StudyDescription", "not available")),
                "modality": str(getattr(dataset, "Modality", "not available")),
                "rows": str(getattr(dataset, "Rows", "not available")),
                "columns": str(getattr(dataset, "Columns", "not available")),
            }
        except Exception:
            pass

    summary = (
        f"This imaging source was recognized as a DICOM-style file. "
        f"Detected modality is {meta['modality']}, study description is {meta['study_description']}, "
        f"and matrix size is {meta['rows']} x {meta['columns']}. "
        "This first-pass summary should be followed by series-level QC, metadata validation, and visual review."
    )

    studio_cards = [
        {"id": "qc", "title": "Imaging QC", "subtitle": "Basic file and metadata checks"},
        {"id": "metadata", "title": "DICOM Metadata", "subtitle": "Patient and study-level tags"},
        {"id": "series", "title": "Series Review", "subtitle": "Image organization view"},
        {"id": "report", "title": "Report Draft", "subtitle": "Grounded narrative summary"},
    ]
    artifacts = {
        "qc": {
            "file_size_bytes": len(raw),
            "dicom_detected": True,
        },
        "metadata": meta,
        "series": {
            "note": "Series-level review will expand when multi-file studies are supported.",
        },
        "report": {
            "draft": summary,
        },
    }
    return IntakeSummaryResponse(
        source=UploadedSourceSummary(
            file_name=file_name,
            file_type=suffix,
            modality="medical-image",
            size_bytes=len(raw),
            status="parsed",
        ),
        grounded_summary=summary,
        studio_cards=studio_cards,
        artifacts=artifacts,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/intake/upload", response_model=IntakeSummaryResponse)
async def upload_source(file: UploadFile = File(...)) -> IntakeSummaryResponse:
    raw = await file.read()
    modality, suffix = _guess_modality(file.filename or "")
    if modality == "clinical-table":
        return _summarize_table(file.filename or "uploaded.csv", raw, suffix)
    if modality == "medical-image":
        return _summarize_dicom(file.filename or "uploaded.dcm", raw, suffix)

    summary = (
        "The uploaded source was received, but this first scaffold currently supports clinical CSV/TSV files "
        "and single-file DICOM uploads only."
    )
    return IntakeSummaryResponse(
        source=UploadedSourceSummary(
            file_name=file.filename or "uploaded-file",
            file_type=suffix,
            modality=modality,
            size_bytes=len(raw),
            status="unsupported",
        ),
        grounded_summary=summary,
        studio_cards=[],
        artifacts={"report": {"draft": summary}},
    )
