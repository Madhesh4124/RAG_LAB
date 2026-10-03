import os
import requests
from dotenv import load_dotenv

load_dotenv()
google_key = os.getenv("GOOGLE_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

gemini_candidates = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
    "gemini-2.5-pro",
]

print("=== TESTING GOOGLE/GEMINI MODELS ===")
for m in gemini_candidates:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={google_key}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": "Hello, answer in 1 word"}]}]}, timeout=10)
        if r.status_code == 200:
            ans = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"[OK] {m}: {ans}")
        else:
            err = r.json().get("error", {}).get("message", "")[:70]
            print(f"[ERR {r.status_code}] {m}: {err}")
    except Exception as e:
        print(f"[EXC] {m}: {e}")

print("\n=== TESTING GROQ MODELS ===")
groq_candidates = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
for gm in groq_candidates:
    url = "https://api.groq.com/openai/v1/chat/completions"
    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={"model": gm, "messages": [{"role": "user", "content": "Hi, 1 word"}], "max_tokens": 10},
            timeout=10,
        )
        if r.status_code == 200:
            ans = r.json()["choices"][0]["message"]["content"].strip()
            print(f"[OK] {gm}: {ans}")
        else:
            err = r.json().get("error", {}).get("message", "")[:70]
            print(f"[ERR {r.status_code}] {gm}: {err}")
    except Exception as e:
        print(f"[EXC] {gm}: {e}")
