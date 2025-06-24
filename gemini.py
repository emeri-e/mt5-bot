import re
import json
import google.generativeai as genai
from config import base

genai.configure(api_key=base.GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

def call_ai_parser(text: str) -> dict:
    prompt = f"""
You are a forex trading assistant bot. Analyze this Telegram message and return structured JSON as explained below.

1. Determine if this message is a NEW trade signal or an UPDATE instruction.
2. Respond ONLY with one of the following valid JSON formats (never include explanations or markdown code blocks):

### NEW trade signal format:
{{
  "type": "new",
  "pair": "XAUUSD",      // MUST NOT be null. Guess based on price if not stated (e.g., price > 1000 = GOLD/XAUUSD)
  "direction": "BUY",    // Must be BUY or SELL
  "entry": 1910.5,       // Use float
  "sl": 1895.0,          // Use float
  "tp1": 1920.0,         // Optional but at least 1 TP is preferred
  "tp2": 1930.0,
  ...
}}

### UPDATE instruction format:
{{
  "type": "update",
  "actions": [
    {{"type": "change_entry", "value": 3129}},
    {{"type": "modify_sl", "value": 3119}},
    {{"type": "modify_sl", "value": "be"}},   // 'be' means breakeven
    {{"type": "close_trade"}},
    {{"type": "note", "text": "TP 3 hit! boom boom"}}
  ]
}}

Rules:
- DO NOT return null or empty fields.
- If pair is not explicitly stated, guess based on price:
  - XAUUSD or GOLD and BTCUSD is the most popular.
- If you can't extract a TP/SL, return fewer TPs or infer logically.
- All numbers must be parsed as floats.
- make sense of what commas or dots mean (e.g., "105.345" means 105345 for btcusd since btc price is big).
- gold(xauusd) is in a few thousands say $3k
- if dot doesnt mean float, then remove it(as in the btc example)
- Always return JSON ONLY.

Telegram message:
{text}
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        json_text = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()

        # Ensure it's valid JSON before returning
        # return json.loads(json_text)
        return json_text
    except Exception as e:
        print(f"Gemini error: {e}")
        return None
