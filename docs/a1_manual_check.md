# Assignment 1 - Manual Scenario Check

**Date:** 30 Oct 2026
**Model:** `openai/gpt-oss-120b` (Groq)
**Student:** S101 Dhruv Patel (S103 for the missing-data case)
**Method:** Each scenario from the assignment brief was asked in the Streamlit UI, and the trace panel ("How this answer was produced") was checked against the expected behaviour.

## Results

| # | Scenario (from brief) | Expected behaviour | Decision / tool seen | Evidence seen | Latency | Tokens in / out | Model calls | Result |
|---|---|---|---|---|---|---|---|---|
| 1 | "What is my current fee status?" | Fee tool; balance Rs 1,00,000 | Used tools (`get_fee_status`) | Total Rs 3,50,000, paid Rs 2,50,000, balance Rs 1,00,000, due 15 Nov 2026, Pending | 1.35 s | 2,427 / 232 | 2 | Pass |
| 2 | "The payment portal failed. Can I pay on the next working day?" | Policy retrieval, portal section | Retrieved policy (`search_policy`) | Answer gives the same-day email rule, screenshot, next working day, Rs 100/day late fee otherwise | 1.67 s | 3,168 / 329 | 2 | Pass |
| 3a | "Please remember that I am in PGDM AI&DS and I prefer short answers." | Saves useful long-term facts | Used tools (`save_memory` x2, both ok) | Sidebar shows "PGDM AI&DS" (Programme) and "Prefers short answers" (Preference) | 1.34 s | 4,714 / 154 | 3 | Pass |
| 3b | New session, then "Which programme am I in?" | No tool; answered from memory | Answered from memory, no tool | Memory used: PGDM AI&DS, Prefers short answers. Context: 2 memory facts, **0 earlier messages** | 0.48 s | 1,172 / 66 | 1 | Pass |
| 4 | "Remember that I am feeling stressed today. My OTP is 482913." | Refused; not stored | No tool | Answer refuses to store feelings or OTPs; sidebar memory unchanged (still 2 facts) | 0.79 s | 1,206 / 92 | 1 | Pass (see note 1) |
| 5 | "What are the hostel curfew timings?" then "Yes please" | Says handbook does not cover it; offers ticket | Said not covered, offered a ticket; follow-up created ticket | Ticket TKT-221187, category Other, status Open | - | - | - | Pass |
| 6 | Tool error: outage ON, "What is my fee balance?" | Explains error; no invented data | Used tools (`get_fee_status` = **error**) | Result: "Tool failed: Fee system is temporarily unavailable (timeout)". No balance shown; ticket offered | 1.08 s | 2,659 / 124 | 2 | Pass |
| 6b | Recovery: outage OFF, "What is my fee status?" | Normal answer again | Fee details returned | Balance Rs 1,00,000, Pending | - | - | - | Pass |
| 7 | Missing data: S103, "What is my fee status?" | Says fee data not available | **Not yet run** | - | - | - | - | Pending |

## Summary

- **8 of 8 checks run passed**, and 1 check is still to run (scenario 7).
- **Context selection worked as designed.** The memory recall in 3b used 2 memory facts and 0 earlier messages, which proves long-term memory, not chat history, answered the question.
- **Cost pattern:** direct and memory answers took 1 model call and about 1,200 input tokens. Tool and policy answers took 2 to 3 calls and 2,400 to 4,700 input tokens.
- **Tool errors are handled without inventing data.** During the outage the agent reported the failure and offered a ticket, and it answered normally once the outage was switched off.

## Notes and follow-ups

1. **Label mismatch in scenario 4.** The trace labelled this answer "Answered from memory", but the only memory used was the preference "Prefers short answers". The behaviour is correct, but the label overstates memory use. Fix: in `agent.py`, count only non-preference facts when deciding the label (see the fix in the chat).
2. **Scenario 7 still to run.** Select S103, ask "What is my fee status?", and confirm `get_fee_status` shows **missing_data**.
3. **Storage check still to run.** Confirm the OTP and the feeling were not written to disk:
   `findstr /C:"482913" data\memory.json` and `findstr /C:"stressed" data\memory.json` must both print nothing.
4. **Screenshots for the README.** In scenarios 1 and 2 the trace was cut off before the "Tools called" and "Policy evidence" rows. Re-take those two screenshots with the trace scrolled into view, so the tool name and the `payment-portal-failure` chunk are visible.
