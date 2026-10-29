"""
memory.py - Long-term memory for the Student Support Agent.

- Stores useful long-term facts per student in data/memory.json
- Blocks sensitive (OTP, password, card...) and temporary information IN CODE
- Selects only the memory items relevant to the current question
"""
import json
import re
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "data" / "memory.json"
CATEGORIES = ("programme", "preference", "other")
MAX_FACT_LEN = 200

# ---------- Filters (enforced in code, not by the LLM) ----------
SENSITIVE_PATTERNS = [
    r"\b(otp|one[- ]time password|password|passwd|pwd|passcode|pin|cvv|cvc)\b",
    r"\b(card number|credit card|debit card|bank account|account number|ifsc|upi pin)\b",
    r"\b(aadhaar|aadhar|pan number|pan card)\b",
    r"\b\d{12,19}\b",            # long numbers (card / account / aadhaar)
    r"\[REDACTED\]",
]
TEMPORARY_PATTERNS = [
    r"\b(today|tonight|right now|at the moment|this moment|currently|this morning|this evening)\b",
    r"\b(feeling|feel|stressed|tired|sick|angry|upset|sad|hungry)\b",
    r"\b(for now|temporarily|just now)\b",
]
SENSITIVE_RE = re.compile("|".join(SENSITIVE_PATTERNS), re.IGNORECASE)
TEMPORARY_RE = re.compile("|".join(TEMPORARY_PATTERNS), re.IGNORECASE)


def check_fact(fact):
    """Return (allowed: bool, reason: str)."""
    if not fact or not fact.strip():
        return False, "Empty fact."
    if len(fact) > MAX_FACT_LEN:
        return False, "Fact too long - only short, useful facts are stored."
    if SENSITIVE_RE.search(fact):
        return False, "Sensitive information (OTP, password, card or ID numbers) is never stored."
    if TEMPORARY_RE.search(fact):
        return False, "Temporary information is not stored as long-term memory."
    return True, "OK"


# ---------- Storage ----------
def _load_all():
    if not MEMORY_FILE.exists():
        return {}
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}           # corrupted file -> start fresh instead of crashing


def _save_all(data):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_memory(student_id):
    """All memory items for one student (never another student's)."""
    return _load_all().get(student_id, [])


def save_memory(student_id, fact, category="other"):
    """Validate and store a fact. Returns a result dict for the agent/trace."""
    fact = (fact or "").strip()
    allowed, reason = check_fact(fact)
    if not allowed:
        return {"saved": False, "reason": reason}
    if category not in CATEGORIES:
        category = "other"

    data = _load_all()
    items = data.setdefault(student_id, [])
    if any(i["fact"].lower() == fact.lower() for i in items):
        return {"saved": False, "reason": "Already remembered.", "fact": fact}
    if category == "programme":              # only one programme fact - replace old one
        items[:] = [i for i in items if i["category"] != "programme"]

    item = {"id": f"mem-{len(items) + 1}-{datetime.now().strftime('%H%M%S')}",
            "fact": fact, "category": category,
            "saved_at": datetime.now().isoformat(timespec="seconds")}
    items.append(item)
    _save_all(data)
    return {"saved": True, "fact": fact, "category": category, "id": item["id"]}


def clear_memory(student_id):
    data = _load_all()
    data.pop(student_id, None)
    _save_all(data)


# ---------- Context selection: only relevant memory ----------
STOPWORDS = {"i", "me", "my", "am", "is", "are", "the", "a", "an", "what", "which", "do",
             "does", "you", "your", "to", "in", "of", "and", "or", "for", "on", "can",
             "how", "remember", "please", "that", "it", "be", "with", "about", "know"}
SYNONYMS = {"course": "programme", "program": "programme", "specialisation": "programme",
            "specialization": "programme", "branch": "programme", "degree": "programme",
            "prefer": "preference", "preferences": "preference", "like": "preference"}
RECALL_RE = re.compile(r"\b(what do you (remember|know)|about me|my details|my profile)\b", re.I)


def _words(text):
    words = re.findall(r"[a-z0-9&]+", text.lower())
    return {SYNONYMS.get(w, w) for w in words if w not in STOPWORDS}


def select_relevant_memory(student_id, question):
    """
    Return only the memory items needed for this question.
    - Preferences are always included (they shape every answer).
    - Other facts are included only if they share a meaningful word with the question.
    - "What do you remember about me?" returns everything.
    """
    items = load_memory(student_id)
    if RECALL_RE.search(question or ""):
        return items
    q_words = _words(question or "")
    selected = []
    for item in items:
        fact_words = _words(item["fact"]) | {item["category"]}
        if item["category"] == "preference" or q_words & fact_words:
            selected.append(item)
    return selected
