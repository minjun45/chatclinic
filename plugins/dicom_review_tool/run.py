from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from app.main import _summarize_dicom, _summarize_dicom_series


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    files = payload.get("files") or []
    if not files:
        raise ValueError("dicom_review_tool requires one or more files")

    normalized = []
    for item in files:
        raw = base64.b64decode(item["raw_base64"])
        normalized.append(
            (
                str(item.get("file_name", "uploaded-file")),
                raw,
                str(item.get("suffix", "dicom")),
                item.get("source_path"),
            )
        )

    if len(normalized) == 1:
        file_name, raw, suffix, source_path = normalized[0]
        response = _summarize_dicom(file_name, raw, suffix, source_path=source_path)
    else:
        response = _summarize_dicom_series(normalized)

    result = response.model_dump()
    result["used_tools"] = ["dicom_review_tool"]
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
