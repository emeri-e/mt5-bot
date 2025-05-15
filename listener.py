import json
import os
import requests
from telethon import TelegramClient, events
import logging
import re
from config import base
from functions import get_order_id_by_message_id, log_new_trade, log_trade_update, update_trade_status
from mt5.utils import handler as h #type: debug


# === Logging Setup ===
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'listener.log')

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


def send(data):
    trading_bot_url = 'http://127.0.0.1:1960/trade_signal'
    try:
        response = requests.post(trading_bot_url, json=data)
        if response.status_code == 200:
            logger.info("Signal sent successfully to the trading bot")
            return response.json()  
        else:
            logger.warning(f"Failed to send signal: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending signal: {e}")
    
    return None


def parse_trade_signal(text):
    data = {}

    # Normalize text
    lines = text.upper().splitlines()
    flat_text = ' '.join(lines)

    # Detect pair
    for curr in base.POPULAR_CURRENCIES:
        matches = re.finditer(rf'([A-Z]{{3,4}}){curr}', flat_text)
        for m in matches:
            symbol = m.group(0)
            if symbol != curr and len(symbol) >= 6:
                data['pair'] = symbol
                break
        if 'pair' in data:
            break
    else:
        if 'GOLD' in flat_text or 'XAU' in flat_text:
            data['pair'] = 'XAUUSD'

    # Direction
    if "BUY" in flat_text and "SELL" not in flat_text:
        data['direction'] = 'BUY'
    elif "SELL" in flat_text and "BUY" not in flat_text:
        data['direction'] = 'SELL'
    elif "BUY" in flat_text and "SELL" in flat_text:
        buy_idx = flat_text.find("BUY")
        sell_idx = flat_text.find("SELL")
        data['direction'] = 'BUY' if buy_idx < sell_idx else 'SELL'

    # Entry
    entry_match = re.search(r'ENTRY(?: PRICE)?[:\s]*([0-9.]+)', flat_text)
    if not entry_match:
        for line in lines:
            if "ENTRY" in line:
                match = re.search(r'([0-9.]+)', line)
                if match:
                    entry_match = match
                    break
    if entry_match:
        data['entry'] = entry_match.group(1)

    # SL 
    sl_match = re.search(r'(STOP ?LOSS|SL)[:\s]*([0-9.]+)', flat_text)
    if not sl_match:
        for line in lines:
            if "SL" in line or "STOP LOSS" in line:
                match = re.search(r'([0-9.]+)', line)
                if match:
                    data['sl'] = match.group(1)
                    break
    else:
        data['sl'] = sl_match.group(2)

    # TPs
    tps = re.findall(r'TP[0-9]*[:\s]*([0-9.]+)', flat_text)
    if not tps:
        for line in lines:
            if line.strip().startswith('TP'):
                match = re.search(r'([0-9.]+)', line)
                if match:
                    tps.append(match.group(1))
    if tps:
        for i, tp in enumerate(tps):
            data[f'tp{i+1}'] = tp

    return data if 'pair' in data and 'direction' in data else None

def parse_update_instruction(text):
    text = text.lower().strip()
    actions = []

    if "move sl to be" in text or "move stop to breakeven" in text:
        actions.append({"type": "modify_sl", "value": "be"})  

    if "close trade" in text:
        actions.append({"type": "close_trade"})

    if "tp" in text and "hit" in text:
        match = re.search(r"tp\s*(\d+)", text)
        if match:
            tp_level = match.group(1)
            actions.append({"type": "tp_hit", "tp": tp_level})
        else:
            actions.append({"type": "tp_hit"})

    return actions if actions else [{"type": "note", "text": text}]


def is_new_trade_message(text):
    text_upper = text.upper()
    return (
        any(keyword in text_upper for keyword in ['BUY', 'SELL']) and 
        len(text) > 25 and 
        len(text.splitlines()) > 5
    )

def is_update_message(text):
    keywords = ['TP', 'MOVE SL', 'CLOSE TRADE']
    text_upper = text.upper()
    return any(k in text_upper for k in keywords)


async def select_channel_to_monitor():
    await telegram_client.connect()
    dialogs = await telegram_client.get_dialogs()

    channels = [d for d in dialogs if d.is_channel]
    if not channels:
        print("No channels or groups found.")
        return

    print("Select a channel/group to monitor:")
    for i, dialog in enumerate(channels):
        print(f"{i + 1}. {dialog.name} (ID: {dialog.entity.id})")

    while True:
        try:
            selection = int(input("Enter the number of the channel to monitor: "))
            if 1 <= selection <= len(channels):
                selected_channel = channels[selection - 1]
                break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    telegram_client.add_event_handler(message_handler, events.NewMessage(chats=selected_channel))
    print(f"Monitoring started for: {selected_channel.name} (ID: {selected_channel.entity.id})")


# @telegram_client.on(events.NewMessage)
async def message_handler(event):
    if not event.message.text:
        return  

    telegram_message = event.message.text  
    message_id = str(event.message.id)

    if is_new_trade_message(telegram_message):
        signal_data = parse_trade_signal(telegram_message)
        if signal_data:
            log_new_trade(message_id, signal_data)

            signal_payload = {
                "type": "new",
                "message_id": message_id,
                "order_id": None,
                "data": signal_data
            }

            # response_data = send(signal_payload)
            response_data = h(signal_payload)

            if response_data and 'order_id' in response_data:
                order_id = response_data['order_id']
                update_trade_status(message_id, order_id)
                logger.info(f"Saved order_id {order_id} for message {message_id}")
            else:
                logger.warning("No order_id returned from trading bot.")

            logger.info(f"Sent NEW trade signal: {signal_payload}")

    elif is_update_message(telegram_message) and event.message.is_reply:
        reply_id = str(event.message.reply_to_msg_id)
        order_id = get_order_id_by_message_id(reply_id)

        if order_id:
            actions = parse_update_instruction(telegram_message)

            update_payload = {
                "type": "update",
                "message_id": message_id,
                "order_id": order_id,
                "data": {"actions": actions}
            }

            # response = send(update_payload)
            response = h(update_payload)

            if response and "results" in response:
                log_trade_update(reply_id, response["results"])
                logger.info(f"Logged update results: {response['results']}")

            logger.info(f"Sent UPDATE signal: {update_payload}")

            
if __name__ == '__main__':
    with telegram_client:
        telegram_client.loop.run_until_complete(select_channel_to_monitor())
        logger.info("Telegram client started and monitoring initialized.")
        telegram_client.run_until_disconnected()

