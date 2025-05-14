import json
import os
import requests
from telethon import TelegramClient, events
import logging
import re
from config import base

# === Logging Setup ===
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, '_.log')

logger = logging.getLogger(__name__)
handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# === Telegram API Setup ===
api_id = base.api_id
api_hash = base.api_hash
session_file = 'user'
telegram_client = TelegramClient(session_file, api_id, api_hash)

# === State Tracking ===
message_mapping = {}
if os.path.exists('message_mapping.json'):
    with open('message_mapping.json', 'r') as f:
        message_mapping = json.load(f)

# def replace_case_insensitive(message, pattern, replacement):
#     return re.sub(pattern, replacement, message, flags=re.IGNORECASE)

def send(signal_text):
    trading_bot_url = 'http://127.0.0.1:1960/trade_signal'
    try:
        response = requests.post(trading_bot_url, json={"signal": signal_text})
        if response.status_code == 200:
            logger.info("Signal sent successfully to the trading bot")
        else:
            logger.warning(f"Failed to send signal: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending signal: {e}")

# === Message Handler ===
@telegram_client.on(events.NewMessage)
async def message_handler(event):
    if not event.message.text:
        return  
    
    telegram_message = event.message.text
    message_id = event.message.id

    if any(keyword in telegram_message.upper() for keyword in ['BUY', 'SELL', 'TP', 'SL', 'ENTRY', 'DONE', 'SUCCESS', 'PIP', 'HIT', 'CLOSE', 'BE', 'SE']):

        send(telegram_message)

        message_mapping[str(message_id)] = telegram_message
        with open('message_mapping.json', 'w') as f:
            json.dump(message_mapping, f, indent=4)

if __name__ == '__main__':
    telegram_client.start()
    logger.info("Telegram client started.")
    telegram_client.run_until_disconnected()
