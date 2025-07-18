import re
import json
from openai import OpenAI
from config import base

client = OpenAI(api_key=base.OPENAI_API_KEY)

def call_ai_parser(text: str) -> dict | None:
    prompt = f"""
You are a forex trading assistant bot. Analyze this Telegram message and return structured JSON as explained below.

1. Determine if this message is a NEW trade signal or an UPDATE instruction.
2. Respond ONLY with one of the following valid JSON formats (never include explanations or markdown code blocks):

NEW trade signal format:
{{
  "type": "new",
  "pair": "XAUUSD",
  "direction": "BUY",
  "entry": 1910.5,
  "sl": 1895.0,
  "tp1": 1920.0,
  "tp2": 1930.0,
  ....
  "tpx": xxxx
}}

UPDATE instruction format:
{{
  "type": "update",
  "actions": [
    {{"type": "change_entry", "value": 3129}},
    {{"type": "modify_sl", "value": 3119}},
    {{"type": "modify_sl", "value": "be"}},
    {{"type": "close_trade"}},
  ]
}}

Rules:
- DO NOT return null or empty fields. 
- If pair is not explicitly stated, guess based on price:
  - Gold (XAUUSD) usually trades between 1,000 - 3,000
  - BTCUSD usually trades above 10,000
- If no TP or SL is found, return what you can.
- All prices must be float.
- Correct improperly formatted prices (e.g., "105.345" for BTC might mean "105345").
- Deduce direction based on relative TP and SL: TP above entry = BUY, TP below = SELL.
- Always return JSON only.
- if there are many new signals, the do for only the last one.
- ignore all update signals on layering( i dont use layering)
- a message can be only update message say ' cancel this trade' or just 'cancel' in such case, just return it as a close_trade

Telegram message:
{text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        print(response)
        raw = response.choices[0].message.content.strip()
        
        json_text = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()

        return json.loads(json_text)
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None
