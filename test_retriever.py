"""test_retriever.py - checks that the retriever returns the right policy chunk."""
from retriever import CHUNKS, retrieve

TESTS = [
    ("The payment portal failed. Can I pay on the next working day?", "payment-portal-failure"),
    ("What is the late fee if I pay after the due date?", "fee-payment-deadline-and-late-fee"),
    ("Can I pay my fees in two installments?", "fee-installments"),
    ("Will I get my money back if I withdraw?", "fee-refund"),
    ("Am I eligible for the merit scholarship with CGPA 8.2?", "merit-scholarship"),
    ("How do I apply for a need-based scholarship? My family income is low.", "need-based-scholarship"),
    ("My scholarship was rejected, can I appeal?", "scholarship-status-and-appeals"),
    ("Can I change my elective after 10 days?", "elective-and-course-change"),
    ("Can I switch from AI&DS to BDA?", "programme-change"),
    ("How do I update my phone number?", "updating-personal-details"),
    ("Can I see another student's data?", "student-data-privacy"),
    ("What happens if my attendance is below 75%?", "attendance"),
    ("I missed my end-term exam due to illness", "end-term-examinations"),
    ("How do I raise a support ticket?", "support-requests-and-escalation"),
    # Not covered by the handbook -> must return nothing
    ("What are the hostel curfew timings?", None),
    ("What is today's canteen menu?", None),
    ("Is there a bus from the railway station to campus?", None),
    ("", None),
]

print(f"{len(CHUNKS)} chunks loaded\n")
passed = 0
for query, expected in TESTS:
    hits = retrieve(query)
    top = hits[0]["id"] if hits else None
    ok = top == expected
    passed += ok
    got = ", ".join(f"{h['id']} ({h['score']})" for h in hits) or "NO MATCH"
    print(f"[{'PASS' if ok else 'FAIL'}] {query[:55]:<55} -> {got}")

print(f"\nResult: {passed}/{len(TESTS)} passed")
print("STEP 3 COMPLETE" if passed == len(TESTS) else "Some tests failed - check above")