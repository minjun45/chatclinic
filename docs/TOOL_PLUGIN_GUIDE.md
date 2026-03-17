# Tool Plugin Guide

This guide explains how collaborators and student teams can add a new tool to `ChatClinic`.

## What to submit

Each team submits one folder under `plugins/`.

```text
plugins/
  team_name_tool/
    tool.json
    run.py
    README.md
    requirements.txt   # optional
```

The default class model is:

- `ChatClinic` provides the shared UI, orchestration Skill, and runner
- collaborators or student teams provide a `tool plugin`
- teams do not need to operate a separate server

## Minimal manifest

Create `tool.json`.

```json
{
  "name": "team_name_tool",
  "team": "team_name",
  "task_type": "analysis-task",
  "modality": "clinical-table",
  "approval_required": true,
  "entrypoint": "run.py",
  "description": "Short human-readable description of the tool."
}
```

Recommended metadata:

```json
{
  "keywords": ["cohort", "sheet", "subject"],
  "recommended_stage": "post-intake",
  "priority": 80,
  "produces": ["cohort_browser"],
  "consumes": ["table_rows"]
}
```

These fields help the orchestration Skill choose tools with less manual hard-coding.

## Execution contract

`ChatClinic` runs the plugin like this:

```bash
python3 run.py --input input.json --output output.json
```

Your script must:

1. read `--input`
2. write `--output`
3. exit with code `0` on success

## Input payload

The runner passes JSON with the current context. A typical payload looks like:

```json
{
  "question": "Explain this cohort",
  "analysis_source": {
    "file_name": "study.xlsx",
    "modality": "clinical-table"
  },
  "analysis_sources": [],
  "analysis_artifacts": {},
  "grounded_summary": "",
  "active_view": null,
  "active_card": {},
  "active_artifact": {}
}
```

Not every field is present for every workflow, so plugins should be defensive.

## Output payload

Write structured JSON like this:

```json
{
  "summary": "Cohort analysis completed.",
  "artifacts": {
    "cohort_browser": {}
  },
  "provenance": {
    "tool_version": "0.1.0"
  }
}
```

Recommended fields:

- `summary`
- `artifacts`
- `provenance`

Useful optional fields:

- `warnings`
- `measurements`
- `preview`
- `report_draft`

## Python template

```python
import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))

    result = {
        "summary": "Tool executed successfully.",
        "artifacts": {},
        "provenance": {"tool_version": "0.1.0"},
    }

    Path(args.output).write_text(json.dumps(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Best practices

- Keep outputs deterministic when possible.
- Return structured artifacts, not only free-form prose.
- Do not assume internet access.
- Do not assume a GPU unless your tool explicitly documents it.
- Do not write outside the plugin working area unless truly needed.
- Emit helpful stderr messages when a run fails.

## How tools are discovered

`ChatClinic` automatically scans `plugins/*/tool.json`.

That means adding a new plugin is usually:

1. create the folder
2. add `tool.json`
3. add `run.py`
4. restart the backend

## How the Skill uses your tool

The orchestration Skill uses:

- `name`
- `task_type`
- `modality`
- `keywords`
- `recommended_stage`
- `priority`

to decide when a tool should be suggested or run.

If your new tool introduces a new analysis path, update:

- `/Users/jongcye/Documents/Codex/workspace/clinical_multimodal_workspace/skills/chatclinic-orchestrator/SKILL.md`

## Recommended collaborator checklist

- `tool.json` is valid JSON
- `name` is unique
- `run.py` works with `--input` and `--output`
- output JSON is valid
- the tool can run in the shared classroom environment
- the result contains useful structured artifacts
- README describes dependencies and expected inputs
