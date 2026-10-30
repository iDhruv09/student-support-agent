"""
evaluate.py - Official evaluation of the Student Support Agent.

Runs a fixed test set through the REAL agent (Groq) and reports, for every test:
  task success, tool used + whether the tool choice was appropriate, latency,
  input/output tokens and the retrieved evidence (policy chunks / memory items).

Usage:
    python evaluate.py a1          # Assignment 1 test set  -> results/a1/
    python evaluate.py a1 --keep   # same, but do NOT reset data/ first

Outputs (in results/<suite>/):
    results.csv      one row per test (open in Excel)
    summary.json     overall numbers
    report.md        evaluation table ready to paste into the README
    traces.jsonl     the full trace of every run in this evaluation
"""
import json
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

import tools
from agent import MODEL, run_agent
from memory import load_memory

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SEED = DATA / "seed" / "students.json"
PAUSE_S = 1.5                      # gap between tests (Groq free-tier rate limits)
SID = "S101"

# ------------------------------------------------------------------ text helpers
DIGITS = str.maketrans("०१२३४५६७८९૦૧૨૩૪૫૬૭૮૯", "01234567890123456789")
NOT_COVERED = ["not cover", "does not", "doesn't", "not include", "no information",
               "not available", "not mention", "couldn't find", "could not find"]


def norm(text):
    """lowercase, straight quotes, normal hyphens and spaces, local digits -> 0-9."""
    t = (text or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    for h in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        t = t.replace(h, "-")
    for sp in ("\u00a0", "\u202f", "\u2009", "\u2007", "\u200a", "\u2002", "\u2003"):
        t = t.replace(sp, " ")
    return t.translate(DIGITS)


def plain_numbers(text):
    """'Rs 1,00,000' -> 'rs 100000' so numbers match in any format."""
    return re.sub(r"(?<=\d),(?=\d)", "", norm(text))


def has_any(text, words):
    """Match ignoring number formatting and spaces ('AI & DS' == 'ai&ds')."""
    t, n = norm(text), plain_numbers(text)
    t_nospace = re.sub(r"\s+", "", t)
    return any(w.lower() in t or w.lower() in n or re.sub(r"\s+", "", w.lower()) in t_nospace
               for w in words)


def memory_text(student=SID):
    return json.dumps(load_memory(student), ensure_ascii=False).lower()


# ------------------------------------------------------------------ A1 test set
# One test per requirement / demo scenario in the Assignment 1 brief.
#   expect_tools : tools that MUST be called      ([] = no tool expected)
#   forbid_tools : tools that must NOT be called
#   chunk        : policy chunk that must be retrieved
#   answer_any   : answer must contain at least one of these
#   answer_none  : answer must contain none of these
#   number       : number that must appear in the answer (any format)
#   check        : extra check, function(trace) -> bool
#   history      : earlier turns [(user, assistant)]
#   setup        : "outage" switches the fee system off for this test
A1_TESTS = [
    dict(id="A1-01", scenario="Fee status (tool use)", q="What is my current fee status?",
         expect_tools=["get_fee_status"], number="100000"),
    dict(id="A1-02", scenario="Portal failed -> policy retrieval",
         q="The payment portal failed. Can I pay on the next working day?",
         expect_tools=["search_policy"], chunk="payment-portal-failure",
         answer_any=["next working day"]),
    dict(id="A1-03", scenario="Scholarship status (tool use)", q="What is my scholarship status?",
         expect_tools=["get_scholarship_status"], answer_any=["merit", "20"]),
    dict(id="A1-04", scenario="Two tools in one question",
         q="How much do I owe, and what happens if I pay after the due date?",
         expect_tools=["get_fee_status", "search_policy"], number="100000", answer_any=["100"]),
    dict(id="A1-05", scenario="Greeting -> answer directly", q="Hi, good morning!",
         expect_tools=[]),
    dict(id="A1-06", scenario="Save useful fact (session 1)",
         q="Please remember that I am in PGDM AI&DS and I prefer short answers.",
         expect_tools=["save_memory"], check=lambda tr: "ai&ds" in memory_text()),
    dict(id="A1-07", scenario="Recall in NEW session (no chat history)",
         q="Which programme am I in?", expect_tools=[], answer_any=["ai&ds", "ai & ds", "ai and ds"],
         check=lambda tr: any(m.get("category") != "preference" for m in tr["evidence"]["memory"])),
    dict(id="A1-08", scenario="Temporary + sensitive not stored",
         q="Remember that I am feeling stressed today. My OTP is 482913.",
         forbid_tools=["get_fee_status", "get_scholarship_status", "search_policy", "create_support_ticket"],
         answer_any=["can't", "cannot", "can not", "not able", "unable", "won't", "never"],
         check=lambda tr: "482913" not in memory_text() and "stressed" not in memory_text()),
    dict(id="A1-09", scenario="Policy gap (hostel)", q="What are the hostel curfew timings?",
         expect_tools=["search_policy"], answer_any=NOT_COVERED, check=lambda tr: not tr["evidence"]["policy_chunks"]),
    dict(id="A1-10", scenario="Tool error (fee system outage)", q="What is my fee balance?",
         setup="outage", expect_tools=["get_fee_status"],
         answer_any=["unavailable", "ticket", "try again", "later"], answer_none=["1,00,000", "100000"]),
   
    dict(id="A1-11", scenario="Create support ticket",
         q="Please raise a ticket: my ID card has not been received yet.",
         expect_tools=["create_support_ticket"], answer_any=["tkt-"]),
]
SUITES = {"a1": A1_TESTS}


# ------------------------------------------------------------------ data reset
def reset_data(out_dir):
    """Start every evaluation from the same clean data. Old files are backed up first."""
    backup = out_dir / "data_backup_before_eval"
    backup.mkdir(parents=True, exist_ok=True)
    for name in ("memory.json", "tickets.json", "traces.jsonl", "pending.json", "audit_log.jsonl"):
        f = DATA / name
        if f.exists():
            shutil.copy(f, backup / name)
            f.unlink()
    if SEED.exists():
        shutil.copy(SEED, DATA / "students.json")


# ------------------------------------------------------------------ scoring
def score(test, tr):
    """Return (tool_appropriate, success, reasons)."""
    used = tr["tools_used"]
    reasons = []

    expect = test.get("expect_tools")
    if expect is None:
        tool_ok = True                                       # no expectation on tools
    elif expect == []:
        tool_ok = not used
        if not tool_ok:
            reasons.append(f"expected no tool, got {used}")
    else:
        missing = [t for t in expect if t not in used]
        tool_ok = not missing
        if missing:
            reasons.append(f"missing tool {missing}")
    bad = [t for t in test.get("forbid_tools", []) if t in used]
    if bad:
        tool_ok = False
        reasons.append(f"should not call {bad}")

    ans = tr["answer"]
    if tr["status"] != "ok":
        reasons.append(f"agent status {tr['status']}")
    if test.get("chunk") and test["chunk"] not in [c["id"] for c in tr["evidence"]["policy_chunks"]]:
        reasons.append(f"chunk {test['chunk']} not retrieved")
    if test.get("answer_any") and not has_any(ans, test["answer_any"]):
        reasons.append("answer missing expected content")
    if test.get("answer_none") and has_any(ans, test["answer_none"]):
        reasons.append("answer contains forbidden content")
    if test.get("number") and test["number"] not in plain_numbers(ans):
        reasons.append(f"number {test['number']} not in answer")
    if test.get("check") and not test["check"](tr):
        reasons.append("extra check failed")

    success = tool_ok and not reasons
    return tool_ok, success, reasons


def evidence_text(tr):
    chunks = [f"{c['id']} ({c['score']:.2f})" for c in tr["evidence"]["policy_chunks"]]
    mems = [f"memory: {m['fact']}" for m in tr["evidence"]["memory"]]
    return "; ".join(chunks + mems) or "-"


# ------------------------------------------------------------------ run
def run_suite(name, keep=False):
    tests = SUITES[name]
    out = ROOT / "results" / name
    out.mkdir(parents=True, exist_ok=True)
    if not keep:
        reset_data(out)

    rows, traces = [], []
    print(f"Evaluating suite '{name}' with {len(tests)} tests on {MODEL}\n")
    for test in tests:
        tools.SIMULATE_OUTAGE["on"] = test.get("setup") == "outage"
        history = []
        for u, a in test.get("history", []):
            history += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
        tr = run_agent(test["q"], test.get("student", SID), history)
        tools.SIMULATE_OUTAGE["on"] = False

        tool_ok, success, reasons = score(test, tr)
        traces.append(tr)
        rows.append({
            "test": test["id"], "scenario": test["scenario"], "student": test.get("student", SID),
            "question": test["q"],
            "expected_tools": ("any (not " + ", ".join(test.get("forbid_tools")) + ")" if test.get("expect_tools") is None
                               else ", ".join(test["expect_tools"]) or "none"),
            "tools_used": ", ".join(tr["tools_used"]) or "none",
            "tool_appropriate": tool_ok, "success": success,
            "decision": tr["decision"], "evidence": evidence_text(tr),
            "latency_s": tr["latency_s"], "llm_calls": tr["llm_calls"],
            "input_tokens": tr["input_tokens"], "output_tokens": tr["output_tokens"],
            "trace_id": tr["trace_id"], "failure_reason": "; ".join(reasons),
            "answer": tr["answer"],
        })
        mark = "PASS" if success else "FAIL"
        print(f"[{mark}] {test['id']} {test['scenario']:<38} tools={tr['tools_used']} "
              f"{tr['latency_s']}s {tr['input_tokens']}/{tr['output_tokens']} tok")
        for r in reasons:
            print(f"        -> {r}")
        time.sleep(PAUSE_S)

    df = pd.DataFrame(rows)
    n = len(df)
    summary = {
        "suite": name, "model": MODEL, "run_at": datetime.now().isoformat(timespec="seconds"),
        "tests": n,
        "passed": int(df.success.sum()),
        "accuracy_pct": round(df.success.mean() * 100, 1),
        "tool_choice_appropriate_pct": round(df.tool_appropriate.mean() * 100, 1),
        "avg_latency_s": round(df.latency_s.mean(), 2),
        "p90_latency_s": round(df.latency_s.quantile(0.9), 2),
        "avg_input_tokens": int(round(df.input_tokens.mean())),
        "avg_output_tokens": int(round(df.output_tokens.mean())),
        "total_tokens": int(df.input_tokens.sum() + df.output_tokens.sum()),
        "failed_tests": df.loc[~df.success, "test"].tolist(),
    }

    df.to_csv(out / "results.csv", index=False, encoding="utf-8-sig")
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (out / "traces.jsonl").open("w", encoding="utf-8") as f:
        for tr in traces:
            f.write(json.dumps(tr, ensure_ascii=False) + "\n")
    (out / "report.md").write_text(report_md(df, summary), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"Accuracy: {summary['passed']}/{n} ({summary['accuracy_pct']}%)  |  "
          f"tool choice appropriate: {summary['tool_choice_appropriate_pct']}%")
    print(f"Latency: avg {summary['avg_latency_s']}s, p90 {summary['p90_latency_s']}s  |  "
          f"tokens avg {summary['avg_input_tokens']} in / {summary['avg_output_tokens']} out")
    print(f"Saved: {out / 'report.md'}")
    return summary


def report_md(df, s):
    yes = lambda v: "Yes" if v else "No"
    lines = [
        f"# Evaluation - suite `{s['suite']}`",
        "",
        f"Model `{s['model']}` · run {s['run_at']} · {s['tests']} tests",
        "",
        "## Summary",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Task accuracy | **{s['passed']}/{s['tests']} ({s['accuracy_pct']}%)** |",
        f"| Tool choice appropriate | {s['tool_choice_appropriate_pct']}% |",
        f"| Latency (avg / p90) | {s['avg_latency_s']} s / {s['p90_latency_s']} s |",
        f"| Avg tokens per question (in / out) | {s['avg_input_tokens']} / {s['avg_output_tokens']} |",
        f"| Total tokens | {s['total_tokens']:,} |",
        "",
        "## Per-test results",
        "",
        "| Test | Scenario | Expected tool | Tool used | Tool OK | Evidence | Latency (s) | Tokens in/out | Result |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in df.itertuples():
        lines.append(f"| {r.test} | {r.scenario} | {r.expected_tools} | {r.tools_used} | "
                     f"{yes(r.tool_appropriate)} | {r.evidence} | {r.latency_s} | "
                     f"{r.input_tokens}/{r.output_tokens} | {'Pass' if r.success else 'Fail'} |")
    failed = df[~df.success]
    lines += ["", "## Failures", ""]
    if len(failed):
        lines += [f"- **{r.test}** {r.scenario}: {r.failure_reason}" for r in failed.itertuples()]
    else:
        lines.append("None.")
    lines += ["", "## Key observations", "",
              "_Write 3-5 observations from the numbers above (cost of tool calls, latency, failures and why)._", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    suite = (args[0] if args else "a1").lower()
    if suite not in SUITES:
        sys.exit(f"Unknown suite '{suite}'. Options: {', '.join(SUITES)}")
    run_suite(suite, keep="--keep" in sys.argv)
