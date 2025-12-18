from __future__ import annotations

from src.orchestrator import run_suite


if __name__ == "__main__":
    log_path = run_suite("src/testsuites/obsidian_suite.yaml")
    print(f"Done. Run log saved to: {log_path}")
