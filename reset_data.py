"""
reset_data.py - Put data/ back to a clean demo state.

Removes runtime files created while testing (memory, tickets, traces) and restores
students.json from data/seed/. Run before tagging a version or recording a demo.

Usage:  python reset_data.py
"""
import shutil
from pathlib import Path

DATA = Path(__file__).parent / "data"
RUNTIME_FILES = ["memory.json", "tickets.json", "traces.jsonl", "pending.json", "audit_log.jsonl"]

removed = []
for name in RUNTIME_FILES:
    f = DATA / name
    if f.exists():
        f.unlink()
        removed.append(name)

seed = DATA / "seed" / "students.json"
if seed.exists():
    shutil.copy(seed, DATA / "students.json")
    print("Restored students.json from data/seed/")

print("Removed:", ", ".join(removed) if removed else "nothing (already clean)")
print("data/ is clean.")
