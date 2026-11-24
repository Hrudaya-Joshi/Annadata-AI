import os
import requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
        self.available = bool(self.api_key)

    def generate(self, prompt, max_tokens=300, temperature=0.3):
        if not self.available:
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            resp = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            return None
        except Exception:
            return None