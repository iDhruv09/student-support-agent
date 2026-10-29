import time
import tools
from agent import run_agent
from memory import clear_memory, load_memory

SID = "S101"
clear_memory(SID)
passed = total = 0


def norm(text):
    """Lowercase + convert curly quotes to straight ones, so keyword checks are reliable."""
    return (text or "").lower().replace("’", "'").replace("‘", "'")


def has_any(text, keywords):
    t = norm(text)
    return any(k in t for k in keywords)


def show(tr):
    print(f"   Answer  : {tr['answer'][:160]}")
    print(f"   Decision: {tr['decision']} | tools={tr['tools_used']} | "
          f"chunks={[c['id'] for c in tr['evidence']['policy_chunks']]}")
    print(f"   Tokens  : in={tr['input_tokens']} out={tr['output_tokens']} | "
          f"LLM calls={tr['llm_calls']} | {tr['latency_s']}s")


def check(name, cond):
    global passed, total
    total += 1
    passed += bool(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}\n")
    time.sleep(1)                      # be gentle with free-tier rate limits


print("1. Greeting -> answer directly")
tr = run_agent("Hi, how are you?", SID); show(tr)
check("no tool used", tr["tools_used"] == [])

print("2. Fee status -> fee tool")
tr = run_agent("What is my current fee status?", SID); show(tr)
check("get_fee_status called and balance mentioned",
      "get_fee_status" in tr["tools_used"]
      and has_any(tr["answer"], ["1,00,000", "100,000", "100000"]))

print("3. Payment portal failed -> policy retrieval")
tr = run_agent("The payment portal failed. Can I pay on the next working day?", SID); show(tr)
check("search_policy used + portal chunk retrieved",
      "payment-portal-failure" in [c["id"] for c in tr["evidence"]["policy_chunks"]])

print("4a. Session 1: save a useful fact")
tr = run_agent("Please remember that I am in PGDM AI&DS and I prefer short answers.", SID); show(tr)
check("memory saved", len(load_memory(SID)) >= 1)

print("4b. NEW session (no history): recall the fact")
tr = run_agent("Which programme am I in?", SID, history=[]); show(tr)
check("answer mentions AI&DS without any tool",
      "ai" in norm(tr["answer"]) and tr["tools_used"] == [])

print("5. Temporary / sensitive statement -> not stored")
before = len(load_memory(SID))
tr = run_agent("Remember that I am feeling very stressed today. Also my OTP is 482913.", SID); show(tr)
mem_text = str(load_memory(SID))
check("nothing new stored, OTP not in memory",
      len(load_memory(SID)) == before
      and "482913" not in mem_text and "stressed" not in mem_text)

print("6. Policy does not cover it -> says so")
tr = run_agent("What are the hostel curfew timings?", SID); show(tr)
check("says handbook does not cover it (and used no policy chunk)",
      not tr["evidence"]["policy_chunks"]
      and has_any(tr["answer"], ["not cover", "does not", "doesn't", "not include",
                                 "no information", "not available", "not mention"]))

print("7. Tool error (simulated outage)")
tools.SIMULATE_OUTAGE["on"] = True
tr = run_agent("What is my fee balance?", SID); show(tr)
tools.SIMULATE_OUTAGE["on"] = False
check("explains problem and offers ticket / retry",
      has_any(tr["answer"], ["unavailable", "ticket", "try again", "later"]))

clear_memory(SID)                      # leave memory clean for the UI demo
print(f"Result: {passed}/{total} passed")
print("STEP 6 COMPLETE" if passed == total else "Some checks failed - paste the output and we will tune it")