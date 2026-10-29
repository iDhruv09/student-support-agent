# check_setup.py - verifies libraries, API key and Groq connection
import os
from dotenv import load_dotenv



print("1. Checking libraries...")
import groq, streamlit, sklearn, pandas
print("   OK - all libraries installed")

print("2. Checking API key...")
load_dotenv(override=True)
key = os.getenv("GROQ_API_KEY")
if not key or not key.startswith("gsk_"):
    print("   ERROR - GROQ_API_KEY missing or wrong in .env")
    raise SystemExit
print("   OK - API key found")

print("3. Testing Groq connection and tool-calling model...")
from groq import Groq
client = Groq(api_key=key)
resp = client.chat.completions.create(
    model=os.getenv("GROQ_MODEL"),
    messages=[{"role": "user", "content": "Reply with only: setup working"}],
    temperature=0,
)
print("   Model reply :", resp.choices[0].message.content)
print("   Input tokens :", resp.usage.prompt_tokens)
print("   Output tokens:", resp.usage.completion_tokens)
print("\nSTEP 1 COMPLETE - everything is ready!")
