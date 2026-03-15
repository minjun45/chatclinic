from __future__ import annotations

import csv
import io
import math
import statistics
from pathlib import Path
from typing import Any, Optional

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


class ChatTurn(BaseModel):
    role: str
    content: str


class ArtifactChatRequest(BaseModel):
    question: str
    analysis: IntakeSummaryResponse
    history: list[ChatTurn] = []
    active_view: Optional[str] = None


class ArtifactChatResponse(BaseModel):
    answer: str


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


def _is_int_like(value: str) -> bool:
    try:
        int(value)
        return True
    except Exception:
        return False


def _is_float_like(value: str) -> bool:
    try:
        float(value)
        return True
    except Exception:
        return False


def _is_date_like(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    date_patterns = (
        r"^\d{4}-\d{2}-\d{2}$",
        r"^\d{4}/\d{2}/\d{2}$",
        r"^\d{2}/\d{2}/\d{4}$",
        r"^\d{2}-\d{2}-\d{4}$",
    )
    import re

    return any(re.match(pattern, value) for pattern in date_patterns)


def _infer_column_profile(name: str, values: list[str]) -> dict[str, Any]:
    non_empty = [value.strip() for value in values if value is not None and value.strip()]
    missing_count = len(values) - len(non_empty)
    unique_values = sorted(set(non_empty))
    unique_count = len(unique_values)
    sample_values = unique_values[:5]
    if not non_empty:
        return {
            "name": name,
            "inferred_type": "empty",
            "non_empty_count": 0,
            "missing_count": missing_count,
            "missing_rate": 1.0 if values else 0.0,
            "unique_count": 0,
            "sample_values": [],
        }

    int_like = all(_is_int_like(value) for value in non_empty)
    float_like = all(_is_float_like(value) for value in non_empty)
    date_like = all(_is_date_like(value) for value in non_empty)

    inferred_type = "categorical"
    numeric_summary: dict[str, Any] | None = None
    if int_like or float_like:
        inferred_type = "integer" if int_like else "float"
        numeric_values = [float(value) for value in non_empty]
        numeric_summary = {
            "min": min(numeric_values),
            "max": max(numeric_values),
            "mean": round(statistics.fmean(numeric_values), 3),
        }
    elif date_like:
        inferred_type = "date-like"
    elif unique_count <= max(12, math.ceil(len(non_empty) * 0.2)):
        inferred_type = "categorical"
    else:
        inferred_type = "free-text"

    return {
        "name": name,
        "inferred_type": inferred_type,
        "non_empty_count": len(non_empty),
        "missing_count": missing_count,
        "missing_rate": missing_count / max(len(values), 1),
        "unique_count": unique_count,
        "sample_values": sample_values,
        "numeric_summary": numeric_summary,
    }


def _build_table_profiles(columns: list[str], rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for column in columns:
        values = [str(row.get(column, "") or "") for row in rows]
        profiles.append(_infer_column_profile(column, values))
    return profiles


def _cohort_summary_from_profiles(rows: list[dict[str, str]], profiles: list[dict[str, Any]]) -> dict[str, Any]:
    categorical_candidates = [item for item in profiles if item["inferred_type"] == "categorical" and item["unique_count"] > 0]
    numeric_candidates = [item for item in profiles if item["inferred_type"] in {"integer", "float"}]
    best_categorical = sorted(categorical_candidates, key=lambda item: item["unique_count"])[0:3]
    best_numeric = numeric_candidates[0:3]

    category_breakdowns = []
    for profile in best_categorical:
        counts: dict[str, int] = {}
        for row in rows:
            value = str(row.get(profile["name"], "") or "").strip() or "(missing)"
            counts[value] = counts.get(value, 0) + 1
        top_values = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]
        category_breakdowns.append(
            {
                "column": profile["name"],
                "top_values": [{"label": label, "count": count} for label, count in top_values],
            }
        )

    numeric_breakdowns = []
    for profile in best_numeric:
        numeric_breakdowns.append(
            {
                "column": profile["name"],
                "summary": profile["numeric_summary"],
            }
        )

    return {
        "record_count": len(rows),
        "field_count": len(profiles),
        "categorical_breakdowns": category_breakdowns,
        "numeric_breakdowns": numeric_breakdowns,
    }


def _summarize_table(file_name: str, raw: bytes, suffix: str) -> IntakeSummaryResponse:
    delimiter = "\t" if suffix == "tsv" else ","
    decoded = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)
    rows = list(reader)
    columns = reader.fieldnames or []
    profiles = _build_table_profiles(columns, rows)
    cohort = _cohort_summary_from_profiles(rows, profiles)
    missing_cells = 0
    for row in rows:
        missing_cells += sum(1 for value in row.values() if value is None or str(value).strip() == "")
    missing_rate = (missing_cells / (max(len(rows), 1) * max(len(columns), 1))) if columns else 0.0

    profile_labels = ", ".join(
        f"{item['name']} ({item['inferred_type']})" for item in profiles[:6]
    )
    cohort_bits: list[str] = []
    if cohort["categorical_breakdowns"]:
        lead = cohort["categorical_breakdowns"][0]
        if lead["top_values"]:
            cohort_bits.append(
                f"{lead['column']} is a useful cohort splitter, led by {lead['top_values'][0]['label']} ({lead['top_values'][0]['count']})"
            )
    if cohort["numeric_breakdowns"]:
        lead_numeric = cohort["numeric_breakdowns"][0]
        summary = lead_numeric["summary"] or {}
        if summary:
            cohort_bits.append(
                f"{lead_numeric['column']} spans {summary.get('min')} to {summary.get('max')} with mean {summary.get('mean')}"
            )

    summary = (
        f"This clinical table contains {len(rows)} row(s) and {len(columns)} column(s). "
        f"The detected schema includes {profile_labels if profile_labels else 'no readable columns'}. "
        f"Current table completeness is approximately {(1 - missing_rate) * 100:.1f}% based on non-empty cells. "
        f"{' '.join(cohort_bits) if cohort_bits else ''} "
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
            "profiles": profiles,
            "sample_rows": rows[:3],
        },
        "cohort": cohort,
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


def _artifact_guided_answer(payload: ArtifactChatRequest) -> str:
    question = payload.question.lower()
    source = payload.analysis.source
    artifacts = payload.analysis.artifacts

    if "schema" in question or "column" in question or "컬럼" in payload.question or "변수" in payload.question:
        profiles = (artifacts.get("schema") or {}).get("profiles", [])
        if not profiles:
            return "No schema profile is available for the current source."
        lines = [
            f"- {item['name']}: {item['inferred_type']} | missing {item['missing_count']} | unique {item['unique_count']} | sample {', '.join(item['sample_values']) if item['sample_values'] else 'n/a'}"
            for item in profiles[:8]
        ]
        return "Schema review of the current source:\n\n" + "\n".join(lines)

    if "cohort" in question or "distribution" in question or "요약" in payload.question or "분포" in payload.question:
        cohort = artifacts.get("cohort") or {}
        lines = [
            f"- records: {cohort.get('record_count', 'n/a')}",
            f"- fields: {cohort.get('field_count', 'n/a')}",
        ]
        for item in (cohort.get("categorical_breakdowns") or [])[:3]:
            values = ", ".join(f"{entry['label']} ({entry['count']})" for entry in item.get("top_values", [])[:4])
            lines.append(f"- {item.get('column')}: {values}")
        for item in (cohort.get("numeric_breakdowns") or [])[:2]:
            summary = item.get("summary") or {}
            lines.append(
                f"- {item.get('column')}: min {summary.get('min', 'n/a')}, max {summary.get('max', 'n/a')}, mean {summary.get('mean', 'n/a')}"
            )
        return "Cohort summary of the current source:\n\n" + "\n".join(lines)

    if "dicom" in question or "metadata" in question or "modality" in question or "영상" in payload.question:
        metadata = artifacts.get("metadata") or {}
        if not metadata:
            return "No imaging metadata is available for the current source."
        return (
            "Imaging metadata summary:\n\n"
            f"- modality: {metadata.get('modality', 'n/a')}\n"
            f"- patient_id: {metadata.get('patient_id', 'n/a')}\n"
            f"- study_description: {metadata.get('study_description', 'n/a')}\n"
            f"- rows: {metadata.get('rows', 'n/a')}\n"
            f"- columns: {metadata.get('columns', 'n/a')}"
        )

    if "qc" in question or "quality" in question or "결측" in payload.question:
        qc = artifacts.get("qc") or {}
        lines = [f"- {key}: {value}" for key, value in qc.items()]
        return "QC summary of the current source:\n\n" + ("\n".join(lines) if lines else "- No QC metrics are available.")

    return (
        f"The current source is `{source.file_name}` ({source.modality}). "
        f"The current grounded summary is:\n\n{payload.analysis.grounded_summary}\n\n"
        "You can ask specifically about schema, cohort, QC, metadata, or the active Studio card."
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


@app.post("/api/v1/chat/artifacts", response_model=ArtifactChatResponse)
def chat_about_artifacts(request: ArtifactChatRequest) -> ArtifactChatResponse:
    return ArtifactChatResponse(answer=_artifact_guided_answer(request))
