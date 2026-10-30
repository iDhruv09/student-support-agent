

import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)   # find agent.py, tools.py, memory.py ... in the project root
os.chdir(ROOT)             # so data/... and app.py paths work too# check_data.py - verifies the data files from Step 2
import json

print("1. Checking students.json...")
students = json.load(open("data/students.json", encoding="utf-8"))
print(f"   {len(students)} students found")
for sid, s in students.items():
    if s["fee_total"] is None:
        fee = "fee data MISSING"
    else:
        fee = f"balance = {s['fee_total'] - s['fee_paid']}"
    print(f"   {sid} {s['name']:<16} {fee:<20} | {s['scholarship']}")

print("2. Checking seed copy...")
seed = json.load(open("data/seed/students.json", encoding="utf-8"))
print("   OK - seed matches" if seed == students else "   ERROR - seed differs")

print("3. Checking policy handbook...")
text = open("data/policy_handbook.md", encoding="utf-8").read()
sections = [p.split("\n")[0].strip() for p in text.split("## ")[1:]]
print(f"   {len(sections)} sections found:")
for s in sections:
    print("   -", s)
print("   Hostel section present?", any("hostel" in s.lower() for s in sections), "(should be False)")

print("\nSTEP 2 COMPLETE")