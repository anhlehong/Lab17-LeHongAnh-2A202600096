"""Run the main assessment files and save separate logs for each run."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_ID = time.strftime("%Y%m%d-%H%M%S")
RUN_DIR = ROOT / "logs" / RUN_ID


def make_log_name(script_path: str) -> str:
    return script_path.replace("\\", "_").replace("/", "_").replace(".", "_") + ".log"


def run_one(name: str, description: str, command: list[str]) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    log_path = RUN_DIR / make_log_name(command[1])
    real_command = [command[0], "-u", *command[1:]]
    print("\n" + "=" * 72, flush=True)
    print(f"Running: {name}", flush=True)
    print(f"Purpose: {description}", flush=True)
    print(f"Command: {' '.join(real_command)}", flush=True)
    print(f"Log file: {log_path}", flush=True)
    print("=" * 72, flush=True)

    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            real_command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=env,
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log_file.write(line)
            log_file.flush()

        process.wait()

    print(f"\n[Done] exit={process.returncode} for {name}", flush=True)

    return {
        "name": name,
        "description": description,
        "command": command,
        "exit_code": process.returncode,
        "log_file": str(log_path.relative_to(ROOT)),
    }


def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    benchmark_json = RUN_DIR / "benchmark_results.json"

    jobs = [
        {
            "name": "Memory backend checks",
            "description": "Kiểm tra 4 memory backends: short-term, profile, episodic, semantic.",
            "command": [sys.executable, "tests/test_memory.py"],
        },
        {
            "name": "Benchmark 10 conversations",
            "description": (
                "Chạy đúng 10 multi-turn conversations và so sánh no-memory vs with-memory "
                "theo rubric."
            ),
            "command": [
                sys.executable,
                "tests/test_conversations.py",
                "--output",
                str(benchmark_json),
            ],
        },
    ]

    print("Assessment runner", flush=True)
    print(f"Run directory: {RUN_DIR}", flush=True)
    print("This run includes:", flush=True)
    for index, job in enumerate(jobs, start=1):
        print(f"{index}. {job['name']} - {job['description']}", flush=True)

    results = [
        run_one(job["name"], job["description"], job["command"])
        for job in jobs
    ]
    summary_path = RUN_DIR / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "run_id": RUN_ID,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 72, flush=True)
    print("Run summary", flush=True)
    print("=" * 72, flush=True)
    print(f"Run directory: {RUN_DIR}", flush=True)
    for item in results:
        print(f"- {item['name']}: exit={item['exit_code']} file={item['log_file']}", flush=True)

    return 0 if all(item["exit_code"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
