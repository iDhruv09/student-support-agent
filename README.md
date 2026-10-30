# Student Support Agent

An AI agent that answers PGDM students' questions about fees, scholarships, course changes and institute policies. One chat interface; the same agent decides for each question whether to answer directly, call a tool, search the policy handbook, or use what it remembers about the student.

Built for the **Agentic AI Engineering** course, PGDM (Big Data Analytics / AI & Data Science), Batch 2025-27.

| Version | Git tag | What it adds |
|---|---|---|
| Assignment 1 | `v1-assignment1` | Agent loop, tools, persistent memory, policy retrieval, context selection, tracing and evaluation |
| Assignment 2 | `v2-assignment2` | Student login, authorization in code, human approval, audit log *(in progress)* |

---

## Architecture

```
Student (Streamlit chat, app.py)
        |  question + selected student ID
        v
AGENT LOOP (agent.py)
  1. Context selection: rules + student ID + relevant memory + last 4 messages + question
  2. LLM call (Groq, tool_choice="auto"): answer directly OR request tool(s)
  3. Run tool(s) -> result goes back to the LLM -> repeat (max 5 calls)
  4. Output guard: stray foreign-script characters -> one rewrite
  5. Trace: tools, evidence, tokens, latency -> data/traces.jsonl
        |
        v
TOOLS (tools.py)
  get_fee_status | get_scholarship_status | search_policy | create_support_ticket | save_memory
        |                    |                      |                   |                 |
  students.json       students.json      retriever.py (TF-IDF)    tickets.json     memory.py (filters)
                                          policy_handbook.md                      memory.json
```

**Key design idea:** the LLM decides *what* to do; Python code runs the tools, filters what may be stored, and records the trace. No agent framework is used, so every step of the loop is visible and explainable.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| LLM | Groq API, `openai/gpt-oss-120b` | Native tool calling; token usage reported on every call |
| Agent | Custom Python loop | Full control over context, tracing and (in A2) authorization |
| UI | Streamlit | Chat interface with a trace panel under each answer |
| Retrieval | TF-IDF + cosine similarity (scikit-learn) | One handbook; scores are easy to show as evidence |
| Storage | JSON files | Readable, easy to inspect during the demo |

## Project structure

```
student-support-agent/
├── app.py               Streamlit chat UI
├── theme.py             Visual theme and UI components (presentation only)
├── agent.py             Agent loop, context selection, tracing, output guard
├── tools.py             Tools, tool schemas, error handling
├── retriever.py         Splits the handbook into sections, TF-IDF search
├── memory.py            Persistent memory, sensitive/temporary filters, relevant-memory selection
├── evaluate.py          Official evaluation -> results/a1/
├── stress_test.py       45 hard and multilingual cases -> results/stress/
├── reset_data.py        Restores data/ to a clean demo state
├── test_files/          Unit and scenario tests (run from the project root, see below)
│   ├── check_setup.py   check_data.py
│   ├── test_retriever.py    test_memory.py    test_tools.py
│   └── test_agent.py        test_ui.py
├── data/
│   ├── students.json         10 sample students (fake data)
│   ├── seed/students.json    clean copy used to reset
│   └── policy_handbook.md    the student policy handbook (14 sections)
├── results/a1/          evaluation report, CSV, summary and traces
├── docs/                manual scenario check and screenshots
├── assets/              logo and favicon
├── .streamlit/config.toml   theme (no secrets)
├── requirements.txt
└── .env.example
```

## Setup and run

1. Clone and create a virtual environment:
   ```bat
   git clone https://github.com/iDhruv09/student-support-agent.git
   cd student-support-agent
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your own key from console.groq.com:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=openai/gpt-oss-120b
   ```
3. Run the app:
   ```bat
   streamlit run app.py
   ```
4. In the sidebar, pick a demo student (S101 is the main demo user) and ask a question, or click one of the demo questions.

**Demo students:** S101 has a Rs 1,00,000 balance and a merit scholarship; S102 is fully paid; S103 has missing fee data (used for the missing-information scenario).

## Tools

| Tool | What it does | Data source |
|---|---|---|
| `get_fee_status` | Total, paid, balance, due date; pending / overdue / fully paid; late fee calculated in code | students.json |
| `get_scholarship_status` | Scholarship status | students.json |
| `search_policy` | Returns only the relevant handbook sections, or "no match" | retriever.py |
| `create_support_ticket` | Creates a ticket ID such as TKT-1A2B3C | tickets.json |
| `save_memory` | Stores a useful long-term fact after the code-level filter | memory.json |

## Memory

| Stored | Never stored |
|---|---|
| Programme (one fact; a new one replaces the old) | OTPs, passwords, PINs, card, account or Aadhaar numbers |
| Answer preferences (e.g. short answers, bullet points) | Temporary states ("feeling stressed today") |

- **Long-term memory** lives in `data/memory.json`, keyed by student ID, so it survives "New session" and restarts.
- **Short-term memory** is the last 4 chat messages, cleared by "New session".
- The sensitive and temporary filters run **in Python**, so they still apply if the LLM tries to save something it shouldn't.

## Retrieval and context selection

- The handbook is split into one chunk per `##` section. The top 2 chunks above a minimum similarity score are returned; anything below the score counts as "not covered".
- The model receives only: the rules, the student ID, today's date, **memory relevant to the question**, the last 4 messages and the question, plus tool results when it calls a tool. **The full handbook is never sent.**
- Questions in Hindi, Gujarati or Spanish work because the agent writes search queries in English (a prompt rule), while answering in the student's language.

## Error handling

| Situation | Behaviour |
|---|---|
| Tool failure (sidebar "Simulate fee system outage") | Explains the problem, offers a ticket, invents no data |
| Missing data (S103) | Says the fee details are not available |
| Topic not in the handbook | Says the handbook does not cover it, offers a ticket |
| Out-of-scope request (coding, general knowledge) | Politely declines |
| LLM API error | Retries temporary errors; otherwise a polite fallback message, no crash |
| Foreign-script characters in an answer | Output guard asks for one rewrite, then strips them |

## Tracing

Every answer has a **"How this answer was produced"** panel: decision type, response time, input and output tokens, model calls, tools called with their status, policy evidence with scores, memory used, and what context was sent. Each full trace is also saved to `data/traces.jsonl` with a trace ID.

## Evaluation (Assignment 1)

Run `python evaluate.py a1`. It resets `data/`, runs the test set through the real agent and writes `results/a1/report.md`, `results.csv`, `summary.json` and `traces.jsonl`.

Model `openai/gpt-oss-120b` · run 30 Oct 2026 · 11 tests

| Measure | Result |
|---|---|
| Task accuracy | **11/11 (100%)** |
| Tool choice appropriate | 100% |
| Latency (avg / p90) | 1.22 s / 2.11 s |
| Avg tokens per question (in / out) | 2,402 / 174 |
| Total tokens (11 questions) | 28,336 |

| Test | Scenario | Expected tool | Tool used | Evidence | Latency (s) | Tokens in/out | Result |
|---|---|---|---|---|---|---|---|
| A1-01 | Fee status | get_fee_status | get_fee_status | - | 2.11 | 2427/218 | Pass |
| A1-02 | Portal failed: pay next working day? | search_policy | search_policy | payment-portal-failure (0.41); fee-payment-deadline-and-late-fee (0.25) | 2.19 | 2923/348 | Pass |
| A1-03 | Scholarship status | get_scholarship_status | get_scholarship_status | - | 1.18 | 2392/99 | Pass |
| A1-04 | Two tools in one question | get_fee_status, search_policy | get_fee_status, search_policy | fee-payment-deadline-and-late-fee (0.34); fee-installments (0.23) | 2.08 | 4189/376 | Pass |
| A1-05 | Greeting | none | none | - | 0.51 | 1162/49 | Pass |
| A1-06 | Save useful fact (session 1) | save_memory | save_memory x2 | - | 1.28 | 3739/173 | Pass |
| A1-07 | Recall in a new session | none | none | memory: PGDM AI&DS; Prefers short answers | 0.69 | 1173/66 | Pass |
| A1-08 | Temporary + sensitive statement | no data tools | none | memory: Prefers short answers | 0.58 | 1175/140 | Pass |
| A1-09 | Policy gap (hostel) | search_policy | search_policy | no section retrieved | 0.60 | 2392/172 | Pass |
| A1-10 | Tool error (fee system outage) | get_fee_status | get_fee_status | - | 1.00 | 2397/120 | Pass |
| A1-11 | Create support ticket | create_support_ticket | create_support_ticket | - | 1.19 | 2450/156 | Pass |

Full results: `results/a1/report.md`, `results.csv` (with answers), `summary.json`, `traces.jsonl`.

**Missing-data handling (S103)** was dropped from the automated set after one run hit a temporary Groq API error on that test (0 tokens; the agent returned its polite fallback instead of crashing). It is checked manually instead; see `docs/a1_manual_check.md`.

### Key observations
- **Tool choice was correct in all 11 tests**, including the three where the right decision was *no* tool (greeting, memory recall, OTP statement).
- **Cost follows the decision.** Direct and memory answers took 1 model call and about 1,170 input tokens; single-tool answers about 2,400; saving memory (two `save_memory` calls, 3 model calls) 3,739; the two-tool question 4,189. A tool answer costs roughly twice a direct one.
- **Memory recall worked without chat history.** A1-07 answered from long-term memory with no tool and the fewest tokens of any test.
- **Evidence is traceable.** Every policy answer names the handbook sections and similarity scores; the hostel question retrieved no section, so the agent said the handbook does not cover it instead of guessing.
- **Latency varies between runs** (average 1.22 s here, 3.46 s in an earlier run with the same token counts), which points to Groq free-tier queueing rather than the agent. A range is the honest figure to quote.

### Additional testing

| Test (in `test_files/` unless noted) | What it checks | Result |
|---|---|---|
| `test_retriever.py` | Correct section for 14 policy questions; no match for 4 off-topic ones | 18/18 |
| `test_memory.py` | Storage, sensitive and temporary filters, per-student memory, relevant selection | 21/21 |
| `test_tools.py` | Every tool without the LLM, including errors and missing data | 20/20 |
| `test_agent.py` | The brief's scenarios through the real agent | 8/8 |
| `stress_test.py` (project root) | 45 hard cases: ambiguity, hallucination traps, prompt injection, memory edge cases, multilingual | 44/44 scored (+1 informational) |
| `docs/a1_manual_check.md` | The brief's scenarios checked by hand in the UI, with screenshots | see file |

Run the tests **from the project root** with `-m`, so Python can find the project modules:

```bat
python -m test_files.check_setup
python -m test_files.check_data
python -m test_files.test_retriever
python -m test_files.test_memory
python -m test_files.test_tools
python -m test_files.test_ui
python -m test_files.test_agent      (calls Groq)
python stress_test.py                (calls Groq)
python evaluate.py a1                (calls Groq)
```

**Tuning history (stress test):** 41/44 at baseline -> 43/44 after adding scope, ticket and language rules -> 44/44 after the output language guard and a test fix. Average input tokens rose by about 19% because of the longer system prompt.

## Limitations

- **No authorization in Assignment 1.** Any selected student can ask for another student's record (stress-test case PI5). This is fixed in Assignment 2 with login and a security gate in the tool code.
- TF-IDF matches words, not meaning, so unusual phrasings can miss the right section; embeddings would be the next step.
- JSON files instead of a database; demo data only.
- Automated tests check script and facts but cannot judge wording quality in Gujarati or Hindi.
- The memory filter blocks the word "pin", so a harmless fact like "pin code 380001" would also be rejected (a deliberate safe-side choice).

## Security note

No API keys are stored in this repository. `.env` is listed in `.gitignore`; use `.env.example` as the template.
