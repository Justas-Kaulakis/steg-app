from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DiffResult:
    total_bytes: int
    changed_bytes: int
    first_diffs: List[Tuple[int, int, int]]  # (offset, a, b)


def diff_files(path_a: str, path_b: str, max_list: int = 50) -> DiffResult:
    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        a = fa.read()
        b = fb.read()

    total = min(len(a), len(b))
    changed = 0
    first = []
    for i in range(total):
        if a[i] != b[i]:
            changed += 1
            if len(first) < max_list:
                first.append((i, a[i], b[i]))

    # count extra bytes if sizes differ
    if len(a) != len(b):
        changed += abs(len(a) - len(b))
        total = max(len(a), len(b))

    return DiffResult(total_bytes=total, changed_bytes=changed, first_diffs=first)
