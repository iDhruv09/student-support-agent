import json
import uuid
from datetime import date, datetime
from pathlib import Path

from memory import save_memory
from retriever import retrieve

DATA_DIR = Path(__file__).parent / "data"
STUDENTS_FILE = DATA_DIR / "students.json"
TICKETS_FILE = DATA_DIR / "tickets.json"

LATE_FEE_PER_DAY = 100            # must match the policy handbook
SIMULATE_OUTAGE = {"on": False}   # demo switch for the "tool error" scenario


class ToolError(Exception):
    """A clean, user-explainable tool failure."""


# ---------------- Data helpers ----------------
def load_students():
    try:
        return json.loads(STUDENTS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ToolError("Student records are not available right now.")
    except json.JSONDecodeError:
        raise ToolError("Student records could not be read.")


def get_student(student_id):
    sid = (student_id or "").strip().upper()
    students = load_students()
    if sid not in students:
        raise ToolError(f"No student record found for ID '{sid}'.")
    return sid, students[sid]


# ---------------- Tools ----------------
def get_fee_status(student_id):
    if SIMULATE_OUTAGE["on"]:
        raise ConnectionError("Fee system is temporarily unavailable (timeout).")
    sid, s = get_student(student_id)
    if s.get("fee_total") is None or s.get("fee_paid") is None:
        return {"status": "missing_data", "student_id": sid,
                "message": "Fee details are not available in the record. "
                           "Please raise a support ticket with the Accounts Office."}

    balance = s["fee_total"] - s["fee_paid"]
    result = {"status": "ok", "student_id": sid, "fee_total": s["fee_total"],
              "fee_paid": s["fee_paid"], "balance": balance,
              "due_date": s.get("due_date"), "note": s.get("fee_note")}

    if balance <= 0:
        result["payment_status"] = "Fully paid"
    elif s.get("due_date"):
        days_left = (date.fromisoformat(s["due_date"]) - date.today()).days
        if days_left < 0:
            result["payment_status"] = "Overdue"
            result["days_overdue"] = -days_left
            result["late_fee_so_far"] = -days_left * LATE_FEE_PER_DAY
        else:
            result["payment_status"] = "Pending"
            result["days_until_due"] = days_left
    return result


def get_scholarship_status(student_id):
    sid, s = get_student(student_id)
    status = s.get("scholarship")
    if not status:
        return {"status": "missing_data", "student_id": sid,
                "message": "Scholarship information is not available in the record."}
    return {"status": "ok", "student_id": sid, "scholarship": status}


def search_policy(query):
    if not query or not query.strip():
        raise ToolError("Search query is empty.")
    chunks = retrieve(query)
    if not chunks:
        return {"status": "no_match", "chunks": [],
                "message": "The student handbook does not contain information on this topic."}
    return {"status": "ok",
            "chunks": [{"id": c["id"], "title": c["title"], "score": c["score"],
                        "text": c["text"]} for c in chunks]}


VALID_CATEGORIES = ("fee", "scholarship", "academic", "technical", "record", "other")


def create_support_ticket(student_id, issue, category="other"):
    issue = (issue or "").strip()
    if len(issue) < 5:
        raise ToolError("Please describe the issue in a few words.")
    if category not in VALID_CATEGORIES:
        category = "other"
    sid, _ = get_student(student_id)

    tickets = []
    if TICKETS_FILE.exists():
        try:
            tickets = json.loads(TICKETS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            tickets = []
    ticket = {"ticket_id": "TKT-" + uuid.uuid4().hex[:6].upper(), "student_id": sid,
              "category": category, "issue": issue[:300], "status": "Open",
              "created_at": datetime.now().isoformat(timespec="seconds"),
              "expected_response": "within 2 working days"}
    tickets.append(ticket)
    TICKETS_FILE.write_text(json.dumps(tickets, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", **ticket}


def remember_fact(student_id, fact, category="other"):
    result = save_memory(student_id, fact, category)
    return {"status": "ok" if result["saved"] else "not_saved", **result}


# ---------------- Dispatcher ----------------
TOOL_FUNCTIONS = {
    "get_fee_status": lambda a, uid: get_fee_status(a.get("student_id") or uid),
    "get_scholarship_status": lambda a, uid: get_scholarship_status(a.get("student_id") or uid),
    "search_policy": lambda a, uid: search_policy(a.get("query", "")),
    "create_support_ticket": lambda a, uid: create_support_ticket(uid, a.get("issue", ""),
                                                                  a.get("category", "other")),
    "save_memory": lambda a, uid: remember_fact(uid, a.get("fact", ""), a.get("category", "other")),
}


def execute_tool(name, args, current_user):
    """
    Run a tool chosen by the LLM. Never raises - always returns a dict.
    A1: no authorization yet (added in Assignment 2).
    """
    if name not in TOOL_FUNCTIONS:
        return {"status": "error", "error": f"Unknown tool '{name}'."}
    if not isinstance(args, dict):
        args = {}
    try:
        return TOOL_FUNCTIONS[name](args, current_user)
    except ToolError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:                       # outage, bad data, anything unexpected
        return {"status": "error", "error": f"Tool failed: {e}",
                "suggestion": "Try again later or raise a support ticket."}


# ---------------- Schemas sent to the LLM ----------------
def _fn(name, description, properties, required=()):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": list(required)}}}


_STUDENT_ID = {"student_id": {"type": "string",
               "description": "Student ID like S101. Omit to use the logged-in student."}}

TOOLS_SCHEMA = [
    _fn("get_fee_status",
        "Get a student's PERSONAL fee record: total fee, amount paid, balance, due date, "
        "and whether payment is pending, overdue or fully paid. Use for 'my fees', 'fee balance', "
        "'how much do I owe'.", _STUDENT_ID),
    _fn("get_scholarship_status",
        "Get a student's PERSONAL scholarship status (approved, pending, rejected, withdrawn...). "
        "Use for 'my scholarship'.", _STUDENT_ID),
    _fn("search_policy",
        "Search the official student policy handbook for GENERAL rules: late fee, payment portal "
        "failure, installments, refunds, scholarship eligibility, elective/programme change, "
        "attendance, exams, support. Use for 'can I...', 'what is the rule...', 'how do I...'.",
        {"query": {"type": "string", "description": "Short search query about the rule."}},
        ["query"]),
    _fn("create_support_ticket",
        "Create a support ticket for the logged-in student when they report a problem, ask to "
        "raise a complaint, or when the question cannot be answered from the handbook or records.",
        {"issue": {"type": "string", "description": "Clear one-line description of the issue."},
         "category": {"type": "string", "enum": list(VALID_CATEGORIES)}},
        ["issue"]),
    _fn("save_memory",
        "Save a USEFUL LONG-TERM fact about the logged-in student, such as their programme or "
        "answer preferences. Never use for OTPs, passwords, temporary feelings or one-time events.",
        {"fact": {"type": "string", "description": "Short fact, e.g. 'Prefers short answers'."},
         "category": {"type": "string", "enum": ["programme", "preference", "other"]}},
        ["fact"]),
]