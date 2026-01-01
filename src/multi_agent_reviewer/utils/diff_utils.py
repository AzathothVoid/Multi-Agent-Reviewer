import re
from typing import List, Dict

HUNK_HEADER_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")


def parse_unified_diff(diff_text: str) -> Dict[str, List[Dict]]:
    files = {}
    current_file = None
    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- "):
            a = line[4:].strip()
            i += 1
            if i < len(lines) and lines[i].startswith("+++ "):
                b = lines[i][4:].strip()
                path = b
                if path.startswith("b/") or path.startswith("a/"):
                    path = path[2:]
                current_file = path
                files.setdefault(current_file, [])
        elif line.startswith("@@"):
            m = HUNK_HEADER_RE.match(line)
            if not m:
                i += 1
                continue
            orig_start = int(m.group(1))
            orig_len = int(m.group(2) or "1")
            new_start = int(m.group(3))
            new_len = int(m.group(4) or "1")

            hunk_lines = []
            i += 1
            while (
                i < len(lines)
                and not lines[i].startswith("@@")
                and not lines[i].startswith("--- ")
            ):
                hunk_lines.append(lines[i])
                i += 1
            if current_file:
                files.setdefault(current_file, []).append(
                    {
                        "orig_start": orig_start,
                        "orig_len": orig_len,
                        "start": new_start,
                        "len": new_len,
                        "lines": hunk_lines,
                    }
                )
            continue
        else:
            i += 1
            continue
    return files


def trim_text(s: str, max_chars: int = 20_000) -> str:
    if len(s) <= max_chars:
        return s

    return s[:max_chars] + "\n...TRUNCATED..."
