import os
import time
from dotenv import load_dotenv

load_dotenv()
from langchain_groq import ChatGroq

key = os.getenv("GROQ_API_KEY")
print("Groq key exists:", bool(key))

for model in ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]:
    print(f"Testing {model}...")
    t0 = time.time()
    try:
        llm = ChatGroq(model=model, api_key=key, max_tokens=100)
        res = llm.invoke("Hi, reply with one short sentence")
        print(f"SUCCESS {model} in {round(time.time() - t0, 2)}s: {res.content}")
    except Exception as e:
        print(f"ERROR {model} in {round(time.time() - t0, 2)}s: {e}")
