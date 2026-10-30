"""
app.py - Streamlit chat interface for the Student Support Agent (Assignment 1).

Run with:  streamlit run app.py

What this screen shows
  - one chat where the same agent decides: answer directly, use a tool, retrieve policy, use memory
  - a trace under every answer (tools, policy evidence, memory, tokens, latency)
  - the student's long-term memory, which survives "New session"
  - a switch that simulates a fee-system outage (tool-error scenario)

Note on the typing effect: the agent returns the full answer first (tools need the complete
result), then the screen types it in. Latency in the trace is the agent's real time only.
"""
import streamlit as st

import theme
from agent import MODEL, run_agent
from memory import clear_memory, load_memory
from tools import SIMULATE_OUTAGE, load_students

st.set_page_config(page_title="Student Support Agent", page_icon=theme.favicon(),
                   layout="wide", initial_sidebar_state="auto")
theme.apply()

ss = st.session_state
ss.setdefault("messages", [])      # this session's chat: {"role", "content", "trace", "history_sent"}
ss.setdefault("queued", None)      # question chosen from a demo button

# Scenarios from the assignment brief, as one-click questions: (question, what it shows)
SAMPLES = [
    ("What is my current fee status?", "Tool call: fee record"),
    ("The payment portal failed. Can I pay on the next working day?", "Policy retrieval"),
    ("Please remember that I am in PGDM AI&DS and I prefer short answers.", "Saves long-term memory"),
    ("Which programme am I in?", "Memory recall. Click 'New session' first to test across sessions"),
    ("Remember that I am feeling stressed today. My OTP is 482913.", "Temporary and sensitive: must not be stored"),
    ("What are the hostel curfew timings?", "Not in the handbook: should say so"),
]
AGENT_AVATAR = ":material/support_agent:"
USER_AVATAR = ":material/person:"


# ---------------------------------------------------------------- callbacks
def reset_chat():
    """New session: clears the chat only. Long-term memory is kept."""
    ss.messages = []


def queue_question(text):
    ss.queued = text


# ---------------------------------------------------------------- data
try:
    STUDENTS = load_students()
except Exception as err:                      # missing or broken students.json
    theme.header(MODEL)
    st.error(f"Student records could not be loaded: {err}. Check that data/students.json exists.")
    st.stop()

SIMULATE_OUTAGE["on"] = bool(ss.get("outage", False))     # set before the agent runs


def render_trace(msg):
    with st.expander("How this answer was produced"):
        st.markdown(theme.trace_html(msg["trace"], msg.get("history_sent", 0)), unsafe_allow_html=True)


def render_message(msg):
    with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"] == "user" else AGENT_AVATAR):
        st.markdown(msg["content"])
        if msg.get("trace"):
            render_trace(msg)


def sample_buttons(prefix):
    cols = st.columns(2)
    for i, (question, shows) in enumerate(SAMPLES):
        cols[i % 2].button(question, key=f"{prefix}_{i}", help=shows, use_container_width=True,
                           on_click=queue_question, args=(question,))


# ---------------------------------------------------------------- session panel (top part)
with st.sidebar:
    student_id = st.selectbox("Signed in as", list(STUDENTS), key="student_id", on_change=reset_chat,
                              format_func=lambda sid: f"{sid}  {STUDENTS[sid]['name']}",
                              help="Demo selector: choose who is asking. Switching student starts a new session.")
    st.button("New session", on_click=reset_chat, use_container_width=True,
              help="Clears this chat. Remembered facts are kept.")

# ---------------------------------------------------------------- main: frozen bar + chat
theme.header(MODEL)
theme.intro()

question = st.chat_input("Type your question") or ss.queued
ss.queued = None

if not ss.messages and not question:
    theme.empty_state()
    sample_buttons("sample")
elif ss.messages:
    with st.expander("Demo questions"):
        sample_buttons("more")

for msg in ss.messages:
    render_message(msg)

if question:
    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    user_msg = {"role": "user", "content": question}
    render_message(user_msg)

    with st.chat_message("assistant", avatar=AGENT_AVATAR):
        slot = st.empty()
        slot.markdown(theme.working_html(), unsafe_allow_html=True)         # animated "working" dots
        trace = run_agent(question, student_id, history)
        theme.type_out(slot, trace["answer"])                               # answer types itself in

    ss.messages.append(user_msg)
    ss.messages.append({"role": "assistant", "content": trace["answer"], "trace": trace,
                        "history_sent": min(len(history), 4)})
    st.rerun()          # redraw from saved state: adds the trace, memory and session numbers

# ---------------------------------------------------------------- session panel (rest)
traces = [m["trace"] for m in ss.messages if m.get("trace")]
stats = {"questions": len(traces),
         "avg_latency": sum(t["latency_s"] for t in traces) / len(traces) if traces else 0,
         "in_tokens": sum(t["input_tokens"] for t in traces),
         "out_tokens": sum(t["output_tokens"] for t in traces)}

with st.sidebar:
    memory_items = load_memory(student_id)
    theme.side_title("What I remember", ruled=True)
    theme.memory_chips(memory_items)
    if memory_items:
        if st.button("Clear remembered facts", use_container_width=True, key="clear_mem",
                     help="Programme and preferences are kept between sessions. "
                          "OTPs, passwords and temporary feelings are never stored."):
            clear_memory(student_id)
            st.rerun()

    theme.side_title("This session", ruled=True)
    theme.stats_grid(stats)

    theme.side_title("Demo controls", ruled=True)
    st.toggle("Simulate fee system outage", key="outage",
              help="Makes the fee tool fail so you can show how the agent handles a tool error.")
