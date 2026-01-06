from typing import List
import time


def run_command(cmd: List[str], cwd: str) -> dict:
    import subprocess

    start_time = time.perf_counter()

    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

    end_time = time.perf_counter()

    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
        "duration": end_time - start_time,
    }
