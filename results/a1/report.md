# Evaluation - suite `a1`

Model `openai/gpt-oss-120b` · run 2026-10-30T23:50:34 · 11 tests

## Summary

| Measure | Result |
|---|---|
| Task accuracy | **11/11 (100.0%)** |
| Tool choice appropriate | 100.0% |
| Latency (avg / p90) | 1.22 s / 2.11 s |
| Avg tokens per question (in / out) | 2402 / 174 |
| Total tokens | 28,336 |

## Per-test results

| Test | Scenario | Expected tool | Tool used | Tool OK | Evidence | Latency (s) | Tokens in/out | Result |
|---|---|---|---|---|---|---|---|---|
| A1-01 | Fee status (tool use) | get_fee_status | get_fee_status | Yes | - | 2.11 | 2427/218 | Pass |
| A1-02 | Portal failed -> policy retrieval | search_policy | search_policy | Yes | payment-portal-failure (0.41); fee-payment-deadline-and-late-fee (0.25) | 2.19 | 2923/348 | Pass |
| A1-03 | Scholarship status (tool use) | get_scholarship_status | get_scholarship_status | Yes | - | 1.18 | 2392/99 | Pass |
| A1-04 | Two tools in one question | get_fee_status, search_policy | get_fee_status, search_policy | Yes | fee-payment-deadline-and-late-fee (0.34); fee-installments (0.23) | 2.08 | 4189/376 | Pass |
| A1-05 | Greeting -> answer directly | none | none | Yes | - | 0.51 | 1162/49 | Pass |
| A1-06 | Save useful fact (session 1) | save_memory | save_memory, save_memory | Yes | - | 1.28 | 3739/173 | Pass |
| A1-07 | Recall in NEW session (no chat history) | none | none | Yes | memory: PGDM AI&DS; memory: Prefers short answers | 0.69 | 1173/66 | Pass |
| A1-08 | Temporary + sensitive not stored | any (not get_fee_status, get_scholarship_status, search_policy, create_support_ticket) | none | Yes | memory: Prefers short answers | 0.58 | 1175/140 | Pass |
| A1-09 | Policy gap (hostel) | search_policy | search_policy | Yes | memory: Prefers short answers | 0.6 | 2392/172 | Pass |
| A1-10 | Tool error (fee system outage) | get_fee_status | get_fee_status | Yes | memory: Prefers short answers | 1.0 | 2397/120 | Pass |
| A1-11 | Create support ticket | create_support_ticket | create_support_ticket | Yes | memory: Prefers short answers | 1.19 | 2450/156 | Pass |

## Failures

None.

## Key observations

_Write 3-5 observations from the numbers above (cost of tool calls, latency, failures and why)._
