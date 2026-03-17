# Course Tool Contract

`ChatClinic` can be extended by student teams without running separate servers.

## Submission model

For the standard class project:

- the instructor provides `ChatClinic`
- the instructor maintains the orchestration Skill and shared runner
- each student team submits a **tool plugin**

Student teams normally do **not** need to submit:

- a separate Skill
- a separate MCP server
- a separate web service
- a separate frontend

In other words:

- `Skill` = centrally managed behavior/policy
- `Tool plugin` = student deliverable

## Goal

Each team submits a **plugin tool** that can be discovered and executed by a shared runner.

Examples:

- segmentation
- detection
- diagnosis draft
- image restoration
- FHIR summarization
- cohort analytics

## Directory contract

Each team submits one folder under `plugins/`.

```text
plugins/
  team_segmentation/
    tool.json
    run.py
    requirements.txt
    README.md
```

Optional extras are allowed:

- helper scripts
- model weights
- config files
- reference outputs for validation

## Manifest contract

Use `tool.json`.

```json
{
  "name": "team_cohort_analysis_tool",
  "team": "team_cohort",
  "task_type": "cohort-browser",
  "modality": "clinical-table",
  "approval_required": false,
  "entrypoint": "run.py",
  "description": "Analyzes cohort tables and returns browser-ready artifacts."
}
```

## Execution contract

`ChatClinic` executes:

```bash
python3 run.py --input input.json --output output.json
```

The plugin must:

1. Read `--input`
2. Produce `--output`
3. Exit with code `0` on success

The plugin should:

4. Fail clearly with a useful stderr message on invalid input
5. Avoid writing outside its own working area unless explicitly designed to do so
6. Finish within a reasonable classroom demo time

## Input payload

The runner passes JSON like:

```json
{
  "question": "Segment the lungs from this chest x-ray",
  "analysis_source": {
    "file_name": "CT_small.dcm",
    "modality": "medical-image"
  },
  "artifacts": {
    "metadata": {},
    "series": {}
  }
}
```

## Output payload

The plugin returns structured JSON like:

```json
{
  "summary": "Cohort analysis completed.",
  "artifacts": {
    "cohort_browser": {}
  },
  "provenance": {
    "version": "0.1.0"
  }
}
```

Recommended output fields:

- `summary`
- `artifacts`
- `provenance`

Useful optional fields:

- `warnings`
- `measurements`
- `preview`
- `report_draft`

## Recommended grading criteria

- input/output contract compliance
- deterministic execution
- artifact quality
- explanation quality
- integration with ChatClinic Studio

## Student submission checklist

- `tool.json` is valid JSON
- `name` is unique and stable
- `team` is clearly set
- `task_type` matches the actual function of the tool
- `run.py` works with `--input` and `--output`
- output JSON is valid
- the tool can run on the provided classroom environment
- the result can be rendered in `ChatClinic` as an artifact

## What to avoid

- do not require your own long-running server unless explicitly approved
- do not hard-code absolute paths to a personal machine
- do not assume internet access during execution
- do not rely on manual GUI interaction to finish the task
- do not return only free-form text when structured artifacts are available

## Suggested classroom workflow

1. Instructor provides a shared ChatClinic runner.
2. Each team implements one plugin.
3. ChatClinic proposes a tool call in chat.
4. User approves execution.
5. The tool runs and returns artifacts.
6. Studio visualizes the result.
