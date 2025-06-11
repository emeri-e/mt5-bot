import re
import google.generativeai as genai
from config import base




genai.configure(api_key=base.GEMINI_API_KEY)

model = genai.GenerativeModel('models/gemini-1.5-flash')

def call_ai_parser(text: str) -> dict:
    prompt = f"""
You are a forex trading assistant bot. Analyze this Telegram message and return structured JSON.

1. First, determine if it's a NEW trade signal or an UPDATE instruction.
2. Return only the appropriate JSON below:

If it's a NEW trade:
{{
  "type": "new",
  "pair": "XAUUSD",
  "direction": "BUY" or "SELL",
  "entry": 1910.5,
  "sl": 1895.0,
  "tp1": 1920.0,
  "tp2": 1930.0,
  ...
  "tpX": 1930.0

}}

If it's an UPDATE:
{{
  "type": "update",
  "actions": [
    {{"type": "change_entry", "value": 3129}},
    {{"type": "modify_sl", "value": 3119}},
    {{"type": "close_trade"}},
    {{"type": "note", "text": 'TP 3 hit! boom boom'}}
  ]
}}


- Use float numbers
- Some users may use "." to mean "," in prices like 105.345 meaning 105345 — infer accordingly
- Only respond with valid JSON 
- modify_sl can have value: 'be' for breakeven

Telegram message:
{text}
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        json_text = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()

        return json_text
    except Exception as e:
        print(f"Gemini error: {e}")
        return None
