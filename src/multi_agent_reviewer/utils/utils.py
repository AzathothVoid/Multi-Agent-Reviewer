from typing import List


def run_command(cmd: List[str], cwd: str) -> dict:
    import subprocess

    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
    }
