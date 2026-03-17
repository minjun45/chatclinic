from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PLUGINS_DIR = ROOT / "plugins"


def discover_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    if not PLUGINS_DIR.exists():
        return tools

    for manifest_path in sorted(PLUGINS_DIR.glob("*/tool.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        manifest["plugin_dir"] = str(manifest_path.parent)
        tools.append(manifest)
    return tools


def get_tool(tool_name: str) -> dict[str, Any] | None:
    for tool in discover_tools():
        if tool.get("name") == tool_name:
            return tool
    return None


def run_tool(tool_name: str, payload: dict[str, Any], timeout_seconds: int = 120) -> dict[str, Any]:
    tool = get_tool(tool_name)
    if not tool:
        raise ValueError(f"Unknown tool: {tool_name}")

    plugin_dir = Path(tool["plugin_dir"])
    entrypoint = plugin_dir / str(tool.get("entrypoint", "run.py"))
    if not entrypoint.exists():
        raise ValueError(f"Tool entrypoint not found: {entrypoint}")

    with tempfile.TemporaryDirectory(prefix="chatclinic_tool_") as tmpdir:
        tmp_path = Path(tmpdir)
        input_path = tmp_path / "input.json"
        output_path = tmp_path / "output.json"
        input_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "").strip()
        pythonpath_parts = [str(ROOT)]
        if existing_pythonpath:
            pythonpath_parts.append(existing_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

        completed = subprocess.run(
            ["python3", str(entrypoint), "--input", str(input_path), "--output", str(output_path)],
            cwd=str(plugin_dir),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )

        if completed.returncode != 0:
            raise RuntimeError(
                "Tool execution failed.\n"
                f"tool={tool_name}\n"
                f"returncode={completed.returncode}\n"
                f"stdout={completed.stdout}\n"
                f"stderr={completed.stderr}"
            )

        if not output_path.exists():
            raise RuntimeError(f"Tool completed without creating output file: {output_path}")

        result = json.loads(output_path.read_text(encoding="utf-8"))
        return {
            "tool": {
                "name": tool.get("name"),
                "team": tool.get("team"),
                "task_type": tool.get("task_type"),
                "modality": tool.get("modality"),
                "approval_required": tool.get("approval_required", True),
            },
            "result": result,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
