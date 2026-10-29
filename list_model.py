# list_models.py - shows which Groq models your API key can use
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

for m in sorted(client.models.list().data, key=lambda x: x.id):
    print(m.id)
    