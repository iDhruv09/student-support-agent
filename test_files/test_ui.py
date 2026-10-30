"""
test_ui.py - checks the Streamlit screen WITHOUT calling Groq (no API key needed).

It replaces run_agent with a fake that returns a ready-made trace, then drives the
real app.py with Streamlit's AppTest and checks the screen behaves as designed.

Run:  python test_ui.py
"""
import agent
import theme
from streamlit.testing.v1 import AppTest

passed = total = 0


def check(name, cond):
    global passed, total
    total += 1
    passed += bool(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


def fake_run_agent(question, student_id, history=None, save_trace=True):
    return {"trace_id": "TR-TEST", "student_id": student_id, "question": question, "status": "ok",
            "decision": "used_tools", "tools": [{"step": 1, "tool": "get_fee_status", "args": {},
            "status": "ok", "latency_ms": 0.4, "result": {}}], "tools_used": ["get_fee_status"],
            "evidence": {"policy_chunks": [{"id": "payment-portal-failure", "score": 0.41}], "memory": []},
            "context_memory": [], "llm_calls": 2, "input_tokens": 2400, "output_tokens": 150,
            "total_tokens": 2550, "latency_s": 1.2,
            "answer": f"Fake answer for: {question}. Your **balance** is Rs 1,00,000."}


agent.run_agent = fake_run_agent          # app.py does "from agent import run_agent", so it gets the fake

print("1. Screen loads")
at = AppTest.from_file("app.py", default_timeout=30).run()
check("no exception on first load", not at.exception)
check("student selector lists the students", len(at.sidebar.selectbox[0].options) >= 3)
check("empty state shows the 6 demo question buttons", sum(1 for b in at.main.button) >= 6)
check("no chat messages yet", len(at.chat_message) == 0)

print("\n2. Asking a question")
at.chat_input[0].set_value("What is my current fee status?").run()
check("no exception after a question", not at.exception)
check("user and assistant messages appear", len(at.chat_message) == 2)
check("assistant shows the full answer after typing", "Rs 1,00,000" in at.chat_message[1].markdown[0].value)
check("trace expander is present", any("How this answer was produced" in e.label for e in at.expander))
check("no raw JSON viewer under answers", len(at.json) == 0)

print("\n3. New session")
next(b for b in at.sidebar.button if b.label == "New session").click().run()
check("chat is cleared", len(at.chat_message) == 0)

print("\n4. Switching student")
at.chat_input[0].set_value("Hello").run()
at.sidebar.selectbox[0].select("S102").run()
check("switching student clears the chat", len(at.chat_message) == 0)

print("\n5. Typing effect")
class Slot:
    def __init__(self): self.frames = []
    def markdown(self, text, **_): self.frames.append(text)
slot = Slot()
theme.type_out(slot, "Your **balance** is Rs 1,00,000 and it is due on 15 Nov.", target_s=0.05)
check("answer is shown in several steps", len(slot.frames) > 3)
check("last frame is the exact answer", slot.frames[-1] == "Your **balance** is Rs 1,00,000 and it is due on 15 Nov.")
check("bold text never appears half-written", all(f.count("**") % 2 == 0 for f in slot.frames))

print("\n6. Trace component")
html = theme.trace_html(fake_run_agent("q", "S101"), history_sent=2)
check("trace shows tool name", "get_fee_status" in html)
check("trace shows policy chunk and score", "payment-portal-failure" in html and "0.41" in html)
check("trace shows tokens", "2,400" in html)
check("tool details shown as a table", "Tool call details" in html and "<th>Result</th>" in html)
check("trace escapes HTML", "&lt;b&gt;" in theme.trace_html({"decision": "<b>x</b>"}))
check("trace copes with an empty trace", "trace" in theme.trace_html({}))

print(f"\nResult: {passed}/{total} passed")
print("UI TEST COMPLETE" if passed == total else "Some checks failed - paste the output")
