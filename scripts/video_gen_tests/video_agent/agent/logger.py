"""
Structured logger for the Video Production Agent.

Logs every step, tool call, input, and output to:
  1. stdout (visible in terminal / start.sh)
  2. A JSON log file in the project output directory
  3. The in-memory progress list (for the API to serve)
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class AgentLogger:
    """Captures everything the agent does."""

    def __init__(self, project_dir: str, job_id: str = ""):
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.job_id = job_id
        self.entries: list[dict] = []
        self._log_file = self.project_dir / "agent_log.jsonl"
        self._start_time = time.time()

        # Also open a human-readable log
        self._text_log = self.project_dir / "agent_log.txt"

    def _elapsed(self) -> str:
        s = int(time.time() - self._start_time)
        return f"{s // 60}:{s % 60:02d}"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _write_entry(self, entry: dict) -> None:
        """Append entry to JSONL file and text log."""
        self.entries.append(entry)

        # JSONL
        with open(self._log_file, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

        # Human-readable text
        with open(self._text_log, "a") as f:
            ts = entry.get("elapsed", "")
            level = entry.get("level", "INFO")
            step = entry.get("step", "")
            msg = entry.get("message", "")
            f.write(f"[{ts}] [{level}] [{step}] {msg}\n")
            if entry.get("details"):
                detail_str = json.dumps(entry["details"], default=str, indent=2)
                for line in detail_str.split("\n"):
                    f.write(f"         {line}\n")

    def _print(self, prefix: str, msg: str, color: str = "") -> None:
        """Print to stdout with color."""
        colors = {
            "blue": "\033[94m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "cyan": "\033[96m",
            "dim": "\033[2m",
            "bold": "\033[1m",
            "": "",
        }
        reset = "\033[0m" if color else ""
        c = colors.get(color, "")
        elapsed = self._elapsed()
        print(f"{c}[{elapsed}] {prefix} {msg}{reset}", flush=True)

    # --- Public API ---

    def step(self, step_name: str, message: str) -> None:
        """Log a pipeline step (research, script, video, etc)."""
        self._print(f"▸ [{step_name}]", message, "bold")
        self._write_entry({
            "level": "STEP",
            "step": step_name,
            "message": message,
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def tool_call(self, tool_name: str, inputs: dict[str, Any]) -> None:
        """Log a tool invocation with its inputs."""
        # Truncate large values for display
        display_inputs = {}
        for k, v in inputs.items():
            sv = str(v)
            display_inputs[k] = sv[:200] + "..." if len(sv) > 200 else sv

        self._print(f"  → {tool_name}()", json.dumps(display_inputs, default=str), "cyan")
        self._write_entry({
            "level": "TOOL_CALL",
            "step": tool_name,
            "message": f"Calling {tool_name}",
            "details": {"inputs": display_inputs},
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def tool_result(self, tool_name: str, result: Any, duration_s: float = 0) -> None:
        """Log the result of a tool call."""
        # Summarize result for display
        if isinstance(result, dict):
            summary = {k: (str(v)[:100] + "..." if len(str(v)) > 100 else v) for k, v in result.items()}
        elif isinstance(result, str):
            summary = result[:300] + "..." if len(result) > 300 else result
        elif isinstance(result, list):
            summary = f"[{len(result)} items]"
        else:
            summary = str(result)[:300]

        dur_str = f" ({duration_s:.1f}s)" if duration_s else ""
        self._print(f"  ✓ {tool_name}{dur_str}:", str(summary)[:200], "green")
        self._write_entry({
            "level": "TOOL_RESULT",
            "step": tool_name,
            "message": f"{tool_name} completed{dur_str}",
            "details": {"result_summary": summary, "duration_s": round(duration_s, 2)},
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def tool_error(self, tool_name: str, error: str) -> None:
        """Log a tool error."""
        self._print(f"  ✗ {tool_name}:", error, "red")
        self._write_entry({
            "level": "TOOL_ERROR",
            "step": tool_name,
            "message": f"{tool_name} failed: {error}",
            "details": {"error": error},
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def data(self, label: str, content: Any) -> None:
        """Log data output (script text, source list, etc)."""
        if isinstance(content, (dict, list)):
            display = json.dumps(content, default=str, ensure_ascii=False)
        else:
            display = str(content)

        # Print truncated to terminal, full to log file
        truncated = display[:500] + "..." if len(display) > 500 else display
        self._print(f"  📄 {label}:", truncated, "dim")
        self._write_entry({
            "level": "DATA",
            "step": label,
            "message": label,
            "details": {"content": content},
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def info(self, message: str) -> None:
        """Log a general info message."""
        self._print("  ℹ", message, "")
        self._write_entry({
            "level": "INFO",
            "step": "",
            "message": message,
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def warn(self, message: str) -> None:
        """Log a warning."""
        self._print("  ⚠", message, "yellow")
        self._write_entry({
            "level": "WARN",
            "step": "",
            "message": message,
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def error(self, message: str) -> None:
        """Log an error."""
        self._print("  ✗ ERROR:", message, "red")
        self._write_entry({
            "level": "ERROR",
            "step": "",
            "message": message,
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def done(self, message: str) -> None:
        """Log completion."""
        self._print("  ✔ DONE:", message, "green")
        self._write_entry({
            "level": "DONE",
            "step": "done",
            "message": message,
            "elapsed": self._elapsed(),
            "timestamp": self._timestamp(),
        })

    def get_progress_list(self) -> list[dict]:
        """Return entries for the API progress endpoint."""
        return [
            {"step": e.get("step", ""), "message": e.get("message", ""), "level": e.get("level", "")}
            for e in self.entries
        ]
