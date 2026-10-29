import memory
from memory import save_memory, load_memory, select_relevant_memory, clear_memory

SID, OTHER = "TEST01", "TEST02"
clear_memory(SID); clear_memory(OTHER)
passed = total = 0

def check(name, condition):
    global passed, total
    total += 1; passed += bool(condition)
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")

print("1. Useful facts are stored")
check("programme saved", save_memory(SID, "Programme: PGDM AI&DS", "programme")["saved"])
check("preference saved", save_memory(SID, "Prefers short answers", "preference")["saved"])
check("other fact saved", save_memory(SID, "Interested in the need-based scholarship")["saved"])
check("duplicate not saved twice", not save_memory(SID, "Prefers short answers", "preference")["saved"])

print("\n2. Sensitive facts are blocked")
for f in ["My OTP is 482913", "password: abc@123", "My pwd is hello1",
          "Card number 4111111111111111", "My UPI PIN is 4321", "Aadhaar 1234 5678 9012"]:
    check(f"blocked: {f}", not save_memory(SID, f)["saved"])

print("\n3. Temporary facts are blocked")
for f in ["I am feeling stressed today", "I am tired right now", "Currently at the library"]:
    check(f"blocked: {f}", not save_memory(SID, f)["saved"])

print("\n4. Persistence across sessions (re-read from file)")
check("3 items stored on disk", len(load_memory(SID)) == 3)
check("file has no OTP", "482913" not in memory.MEMORY_FILE.read_text())

print("\n5. Programme is replaced, not duplicated")
save_memory(SID, "Programme: PGDM BDA", "programme")
progs = [i["fact"] for i in load_memory(SID) if i["category"] == "programme"]
check("only one programme fact", progs == ["Programme: PGDM BDA"])
save_memory(SID, "Programme: PGDM AI&DS", "programme")

print("\n6. Memory is per student")
save_memory(OTHER, "Prefers Hindi", "preference")
check("TEST01 cannot see TEST02 memory", all("Hindi" not in i["fact"] for i in load_memory(SID)))

print("\n7. Relevant memory selection")
def facts(q): return [i["fact"] for i in select_relevant_memory(SID, q)]
check("'Which programme am I in?' -> programme + preference",
      set(facts("Which programme am I in?")) == {"Programme: PGDM AI&DS", "Prefers short answers"})
check("'What course am I in?' -> programme (synonym)", "Programme: PGDM AI&DS" in facts("What course am I in?"))
check("'What is the late fee?' -> preference only", facts("What is the late fee?") == ["Prefers short answers"])
check("'What do you remember about me?' -> all", len(facts("What do you remember about me?")) == 3)

clear_memory(SID); clear_memory(OTHER)
print(f"\nResult: {passed}/{total} passed")
print("STEP 4 COMPLETE" if passed == total else "Some tests failed - check above")