#!/usr/bin/env python3
"""
Standalone Groq API connectivity test.
Usage: python test_groq.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the same directory as this script
load_dotenv(Path(__file__).resolve().parent / ".env")


def main():
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key in ("your_groq_api_key_here", "changeme", "placeholder"):
        print("❌ GROQ_API_KEY is missing or is a placeholder.")
        sys.exit(1)

    import requests

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Reply with only the word WORKING"}],
        "temperature": 0.0,
        "max_tokens": 10,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            print(f"✅ Groq API connection successful. Model responded: {content}")
            sys.exit(0)
        else:
            print(f"❌ Groq API returned HTTP {resp.status_code}: {resp.text[:200]}")
            sys.exit(1)
    except Exception as exc:
        print(f"❌ Groq API connection failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
