import asyncio
import json
import os
import sys
import requests
from telethon import TelegramClient, events
import logging
import re
from config import base
from functions import get_order_id_by_message_id, load_accounts, log_new_trade, log_trade_update, save_accounts, update_trade_status

import tkinter as tk
from tkinter import messagebox, ttk



# === Logging Setup ===
if getattr(sys, 'frozen', False):
    # Running as .exe
    base_dir = os.path.dirname(sys.executable)
else:
    # Running as script
    base_dir = os.path.dirname(os.path.abspath(__file__))

log_file = os.path.join(base_dir, 'listener.log')

logger = logging.getLogger('mybot')
handler = logging.FileHandler(log_file, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

from gemini import call_ai_parser
from mt5.utils import handler as h, get_running_orders#type: debug

# === Telegram API Setup ===
api_id = base.api_id
api_hash = base.api_hash
session_file = 'user'
telegram_client = TelegramClient(session_file, api_id, api_hash)

LOT_SIZE = base.lot_size
TP_INDEX = base.tp_index

def show_accounts_settings_window():
    accounts = load_accounts()

    root = tk.Tk()
    root.title("MT5 Bot - Account Setup")
    root.geometry("600x500")
    root.resizable(False, False)

    entries = []

    # === Top frame for "Add Account" button ===
    top_frame = tk.Frame(root)
    top_frame.pack(fill="x", pady=(10, 0))
    tk.Button(top_frame, text="Add Account", command=lambda: add_account_fields()).pack(pady=5)

    # === Create scrollable canvas ===
    canvas = tk.Canvas(root, borderwidth=0)
    scroll_frame = tk.Frame(canvas)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    scroll_frame.bind("<Configure>", on_frame_configure)

    def add_account_fields(account=None):
        frame = tk.Frame(scroll_frame, bd=2, relief="groove", padx=5, pady=5)
        frame.pack(padx=10, pady=5, fill="x")

        lot_var = tk.StringVar(value=str(account.get("lot_size", "")) if account else "")
        tp_var = tk.StringVar(value=str(account.get("tp_index", "")) if account else "")
        login_var = tk.StringVar(value=account.get("login", "") if account else "")
        password_var = tk.StringVar(value=account.get("password", "") if account else "")
        server_var = tk.StringVar(value=account.get("server", "") if account else "")
        username_var = tk.StringVar(value=account.get("username", "") if account else "")
        partial_index_var = tk.StringVar(value=account.get("partial_tp_index", "") if account else "")
        partial_percent_var = tk.StringVar(value=account.get("partial_percent", "") if account else "")

        def remove():
            entries.remove((frame, lot_var, tp_var, login_var, password_var, server_var, username_var))
            frame.destroy()

        tk.Label(frame, text="Lot Size").grid(row=0, column=0)
        tk.Entry(frame, textvariable=lot_var, width=10).grid(row=0, column=1)

        tk.Label(frame, text="TP Index").grid(row=0, column=2)
        tk.Entry(frame, textvariable=tp_var, width=10).grid(row=0, column=3)

        tk.Label(frame, text="Login").grid(row=1, column=0)
        tk.Entry(frame, textvariable=login_var, width=20).grid(row=1, column=1)

        tk.Label(frame, text="Password").grid(row=1, column=2)
        tk.Entry(frame, textvariable=password_var, show="*", width=20).grid(row=1, column=3)

        tk.Label(frame, text="Server").grid(row=2, column=0)
        tk.Entry(frame, textvariable=server_var, width=40).grid(row=2, column=1, columnspan=2)

        tk.Label(frame, text="Username").grid(row=3, column=0)
        tk.Entry(frame, textvariable=username_var, width=30).grid(row=3, column=1, columnspan=2)

        tk.Label(frame, text="Partial TP Index").grid(row=4, column=0)
        tk.Entry(frame, textvariable=partial_index_var, width=10).grid(row=4, column=1)

        tk.Label(frame, text="Partial %").grid(row=4, column=2)
        tk.Entry(frame, textvariable=partial_percent_var, width=10).grid(row=4, column=3)

        tk.Button(frame, text="Remove", command=remove).grid(row=5, column=3)

        entries.append((frame, lot_var, tp_var, login_var, password_var, server_var, username_var, partial_index_var, partial_percent_var))

    for acc in accounts:
        add_account_fields(acc)

    def save_and_start():
        result = []
        for _, lot_var, tp_var, login_var, password_var, server_var, username_var, partial_index_var, partial_percent_var in entries:
            try:
                lot = float(lot_var.get())
                tp = int(tp_var.get())
                if tp < 1:
                    raise ValueError("TP index must be >= 1")

                partial_tp_index = partial_index_var.get().strip()
                partial_percent = partial_percent_var.get().strip()

                result.append({
                    "lot_size": lot,
                    "tp_index": tp,
                    "login": login_var.get(),
                    "password": password_var.get(),
                    "server": server_var.get(),
                    "username": username_var.get(),
                    "partial_tp_index": int(partial_tp_index) if partial_tp_index else None,
                    "partial_percent": float(partial_percent) if partial_percent else None
                })
            except Exception as e:
                messagebox.showerror("Invalid Input", f"One of the accounts has an error:\n{e}")
                return

        save_accounts(result)
        root.destroy()

    # === Bottom "Start Bot" button ===
    # bottom_frame = tk.Frame(root)
    # bottom_frame.pack(pady=10)
    tk.Button(top_frame, text="Start Bot", command=save_and_start).pack()

    root.mainloop()

    
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
        logger.error(f"Error sending signal:{e}")
    
    return None


# def parse_trade_signal(text):
#     data = {}

#     # Normalize text
#     lines = text.upper().splitlines()
#     flat_text = ' '.join(lines)

#     # Detect pair
#     for curr in base.POPULAR_CURRENCIES:
#         matches = re.finditer(rf'([A-Z]{{3,4}}){curr}', flat_text)
#         for m in matches:
#             symbol = m.group(0)
#             if symbol != curr and len(symbol) >= 6:
#                 data['pair'] = symbol
#                 break
#         if 'pair' in data:
#             break
#     else:
#         if 'GOLD' in flat_text or 'XAU' in flat_text:
#             data['pair'] = 'XAUUSD'

#     # Direction
#     if "BUY" in flat_text and "SELL" not in flat_text:
#         data['direction'] = 'BUY'
#     elif "SELL" in flat_text and "BUY" not in flat_text:
#         data['direction'] = 'SELL'
#     elif "BUY" in flat_text and "SELL" in flat_text:
#         buy_idx = flat_text.find("BUY")
#         sell_idx = flat_text.find("SELL")
#         data['direction'] = 'BUY' if buy_idx < sell_idx else 'SELL'

#     # Entry
#     entry_match = re.search(r'ENTRY(?: PRICE)?[:\s]*([0-9.]+)', flat_text)
#     if not entry_match:
#         for line in lines:
#             if "ENTRY" in line:
#                 match = re.search(r'([0-9.]+)', line)
#                 if match:
#                     entry_match = match
#                     break
#     if entry_match:
#         data['entry'] = entry_match.group(1)

#     # SL 
#     sl_match = re.search(r'(STOP ?LOSS|SL)[:\s]*([0-9.]+)', flat_text)
#     if not sl_match:
#         for line in lines:
#             if "SL" in line or "STOP LOSS" in line:
#                 match = re.search(r'([0-9.]+)', line)
#                 if match:
#                     data['sl'] = match.group(1)
#                     break
#     else:
#         data['sl'] = sl_match.group(2)

#     # TPs
#     tps = re.findall(r'TP[0-9]*[:\s]*([0-9.]+)', flat_text)
#     if not tps:
#         for line in lines:
#             if line.strip().startswith('TP'):
#                 match = re.search(r'([0-9.]+)', line)
#                 if match:
#                     tps.append(match.group(1))
#     if tps:
#         for i, tp in enumerate(tps):
#             data[f'tp{i+1}'] = tp

#     return data if 'pair' in data and 'direction' in data else None

# def parse_update_instruction(text:str):
#     actions = []
#     keywords = {
#         "change_entry": [r"(\bchange\s+entry\b)", r"(\bentry\b)"],
#         "modify_sl": [r"(\bsl\b)", r"(\bstop\s*loss\b)", r"(\bstoploss\b)"],
#         "change_tp": [r"(\btp\b)", r"(\btake\s*profit\b)", r"(\btakeprofit\b)"]
#     }

#     # Pre-compile the number pattern and combine all keywords
#     number_pattern = re.compile(r'\d+(?:\.\d+)?')
#     all_keywords = {kw: key for key, patterns in keywords.items() for kw in patterns}

#     # Build one combined regex pattern to match all keywords
#     pattern = re.compile('|'.join(all_keywords.keys()), re.IGNORECASE)

#     # Find all keyword matches and their positions
#     matches = list(pattern.finditer(text))
#     matches.append(None)  # sentinel for end

#     for i in range(len(matches) - 1):
#         kw_match = matches[i]
#         print(kw_match)
#         start = kw_match.end()
#         end = matches[i+1].start() if matches[i+1] else len(text)

#         segment = text[start:end]
#         num_match = number_pattern.search(segment)

#         if num_match:
#             # Map the matched pattern back to its action type
#             matched_pattern = kw_match.group(0).lower()
#             action_type = next(
#                 (action for pattern, action in all_keywords.items() if re.fullmatch(pattern, matched_pattern, re.IGNORECASE)),
#                 None
#             )
#             if action_type:
#                 actions.append({"type": action_type, "value": float(num_match.group())})

#     return actions if actions else [{"type": "note", "text": text}]

def parse_trade_signal(text: str):
    try:
        response = call_ai_parser(text)
        parsed = json.loads(response)
        if parsed.get("type") == "new":
            return {k: v for k, v in parsed.items() if k != "type"}
    except Exception as e:
        print(f"parse_trade_signal failed: {e}")
    return None

def parse_update_instruction(text: str):
    try:
        response = call_ai_parser(text)
        parsed = json.loads(response)
        if parsed.get("type") == "update":
            return parsed.get("actions", [])
    except Exception as e:
        print(f"parse_update_instruction failed: {e}")
    return [{"type": "note", "text": text}]


def is_new_trade_message(text):
    text_upper = text.upper()
    return (
        # any(keyword in text_upper for keyword in ['BUY', 'SELL']) and 
        len(text) > 25 and 
        len(text.splitlines()) > 3
    )

def is_update_message(text):
    keywords = [
        'TP',        
        'SL',         
        'ENTRY',      
        'CLOSE',      
        'CANCEL',     
        'STOP',       
        'REMOVE',     
        'ADJUST',    
        'MOVE',     
        'MODIFY',   
        'UPDATE',   
        'DELETE',  
        'EXIT',   
        'REVISE',  
        'EDIT',   
        'SHIFT',  
        'CHANGE', 
        'WITHDRAW', 
        'TAKE PROFIT' 
    ]
    
    text_upper = text.upper()
    return any(k in text_upper for k in keywords)


async def select_channel_to_monitor():
    await telegram_client.connect()
    dialogs = await telegram_client.get_dialogs()
    channels = [d for d in dialogs if d.is_channel]
    if not channels:
        print("No channels or groups found.")
        return

    # print("Select a channel/group to monitor:")
    selected_channel = None
    for i, dialog in enumerate(channels):
        print(f"{i + 1}. {dialog.name} (ID: {dialog.entity.id})")# if 'fx' in dialog.name.lower() or 'signal' in dialog.name.lower() else None
        if dialog.name == base.SELECTED_CHANNEL:
            selected_channel = dialog
            break
    
    else:
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
# async def message_handler(event):
#     if not event.message.text:
#         return  

#     telegram_message = event.message.text  
#     message_id = str(event.message.id)

#     if is_new_trade_message(telegram_message):
#         signal_data = parse_trade_signal(telegram_message)
#         if signal_data:
#             signal_data['lot'] = LOT_SIZE
#             max_index = TP_INDEX
#             for i in range(max_index, 0, -1):
#                 tp_key = f"tp{i}"
#                 if tp_key in signal_data:
#                     signal_data["tp"] = signal_data[tp_key]
#                     break
#             else:
#                 logger.warning("couldnt get the tp value. skipping trade...")
#                 return
            
#             log_new_trade(message_id, signal_data)

#             signal_payload = {
#                 "type": "new",
#                 "message_id": message_id,
#                 "order_id": None,
#                 "data": signal_data
#             }

#             # response_data = send(signal_payload)
#             response_data = h(signal_payload)

#             if response_data and 'order_id' in response_data:
#                 order_id = response_data['order_id']
#                 update_trade_status(message_id, order_id)
#                 logger.info(f"Saved order_id {order_id} for message {message_id}")
#             else:
#                 logger.warning("No order_id returned from trading bot.")

#             logger.info(f"Sent NEW trade signal: {signal_payload}")

#     elif is_update_message(telegram_message):
#         order_id = None
#         signal_msg_id = None

#         # Case: if message is a reply, fetch order_id from replied-to message
#         if event.message.is_reply:
#             reply_id = str(event.message.reply_to_msg_id)
#             order_id = get_order_id_by_message_id(reply_id)
#             signal_msg_id = reply_id

#         # Case: not a reply — find the latest valid signal message before this one
#         else:
#             async for msg in telegram_client.iter_messages(event.chat_id, max_id=event.message.id - 1):
#                 if msg.text and is_new_trade_message(msg.text):
#                     signal_msg_id = str(msg.id)
#                     order_id = get_order_id_by_message_id(signal_msg_id)
#                     logger.debug(f"Matched with previous trade message ID: {signal_msg_id}")
#                     break

#         if order_id:
#             actions = parse_update_instruction(telegram_message)

#             update_payload = {
#                 "type": "update",
#                 "message_id": str(event.message.id),
#                 "order_id": order_id,
#                 "data": {"actions": actions}
#             }
#             logger.debug(f'update payload = {update_payload}')

#             response = h(update_payload)
#             logger.debug(f'The response is {response}')

#             if response and "results" in response:
#                 log_trade_update(signal_msg_id, response["results"])
#                 logger.info(f"Logged update results: {response['results']}")

#             logger.info(f"Sent UPDATE signal: {update_payload}")
#         else:
#             logger.warning("Could not determine order_id for update message.")

async def message_handler(event):
    if not event.message.text:
        return

    telegram_message = event.message.text
    message_id = str(event.message.id)

    if is_new_trade_message(telegram_message):
        signal_data = parse_trade_signal(telegram_message)
        if not signal_data:
            return

        for account in ACCOUNTS:
            username = account['username']
            lot_size = account['lot_size']
            tp_index = account['tp_index']
            login = account['login']
            password = account['password']
            server = account['server']
            partial_tp_index = account.get("partial_tp_index")
            partial_percent = account.get("partial_percent")

            if partial_tp_index and partial_percent:
                partial_tp_key = f"tp{partial_tp_index}"
                if partial_tp_key not in signal_data:
                    logger.warning(f"[{username}] Partial TP index not found in signal.")
                    continue

                # === Place partial trade ===
                partial_lot = round(lot_size * (partial_percent / 100), 2)
                main_lot = round(lot_size - partial_lot, 2)

                if partial_lot > 0:
                    partial_signal = signal_data.copy()
                    partial_signal["lot"] = partial_lot
                    partial_signal["tp"] = signal_data[partial_tp_key]

                    log_new_trade(username, f"{message_id}-partial", partial_signal)
                    partial_payload = {
                        "type": "new",
                        "message_id": f"{message_id}-partial",
                        "order_id": None,
                        "data": partial_signal
                    }

                    with base.mt5_lock:
                        response = h(partial_payload, login, password, server)
                    if response and response.get('order_id'):
                        update_trade_status(username, f"{message_id}-partial", response["order_id"])
                        

                # === Place remaining trade ===
                if main_lot > 0:
                    main_signal = signal_data.copy()
                    main_signal["lot"] = main_lot

                    for i in range(tp_index, 0, -1):
                        tp_key = f"tp{i}"
                        if tp_key in main_signal:
                            main_signal["tp"] = main_signal[tp_key]
                            break
                    else:
                        logger.warning(f"[{username}] Main TP index not found. Skipping.")
                        continue
                    
                    log_new_trade(username, message_id, main_signal)

                    main_payload = {
                        "type": "new",
                        "message_id": message_id,
                        "order_id": None,
                        "data": main_signal
                    }

                    with base.mt5_lock:
                        response = h(main_payload, login, password, server)
                    if response and 'order_id' in response:
                        update_trade_status(username, message_id, response["order_id"])
                        
            else:

                # Adjust signal per account
                signal_data_for_account = signal_data.copy()
                signal_data_for_account['lot'] = lot_size

                for i in range(tp_index, 0, -1):
                    tp_key = f"tp{i}"
                    if tp_key in signal_data_for_account:
                        signal_data_for_account['tp'] = signal_data_for_account[tp_key]
                        break
                else:
                    logger.warning(f"[{username}] TP index not found. Skipping this account.")
                    continue

                log_new_trade(username, message_id, signal_data_for_account)

                signal_payload = {
                    "type": "new",
                    "message_id": message_id,
                    "order_id": None,
                    "data": signal_data_for_account
                }

                with base.mt5_lock:
                    response_data = h(signal_payload, login, password, server)

                if response_data and response_data.get('order_id'):
                    update_trade_status(username, message_id, response_data['order_id'])
                    logger.info(f"[{username}] Order ID {response_data['order_id']} saved for message {message_id}")
                else:
                    logger.warning(f"[{username}] No order ID returned.")

    elif is_update_message(telegram_message):
        # Try to get the message ID of the signal this update is related to
        signal_msg_id = None

        if event.message.is_reply:
            signal_msg_id = str(event.message.reply_to_msg_id)
        else:
            async for msg in telegram_client.iter_messages(event.chat_id, max_id=event.message.id - 1):
                if msg.text and is_new_trade_message(msg.text):
                    signal_msg_id = str(msg.id)
                    break

        if not signal_msg_id:
            logger.warning("Could not locate previous signal message for update.")
            return

        actions = parse_update_instruction(telegram_message)

        for account in ACCOUNTS:
            username = account['username']
            login = account['login']
            password = account['password']
            server = account['server']
            

            order_id = get_order_id_by_message_id(username, signal_msg_id)
            if not order_id:
                logger.warning(f"[{username}] No order ID found for message {signal_msg_id}. Skipping update.")
                continue

            update_payload = {
                "type": "update",
                "message_id": message_id,
                "order_id": order_id,
                "data": {"actions": actions}
            }

            with base.mt5_lock:
                response = h(update_payload, login, password, server)

            if response and "results" in response:
                log_trade_update(username, signal_msg_id, response["results"])
                logger.info(f"[{username}] Logged update: {response['results']}")
            else:
                logger.warning(f"[{username}] Update failed or no results returned.")


    
# # === Main Entry Point ===
# async def main():
#     from interface import dp, bot
#     global ACCOUNTS

#     show_accounts_settings_window()
#     ACCOUNTS = load_accounts()

#     bot_task = asyncio.create_task(dp.start_polling(bot))
#     async with telegram_client:
#         await select_channel_to_monitor()
#         logger.info("Telegram client started and monitoring initialized.")
#         await telegram_client.run_until_disconnected()
    
# if __name__ == '__main__':
#     # global ACCOUNTS
#     asyncio.run(main())


async def main():
    from interface import create_bot_app

    global ACCOUNTS
    show_accounts_settings_window()
    ACCOUNTS = load_accounts()

    app = create_bot_app()

    # bot_task = asyncio.create_task(app.run_polling())
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    async with telegram_client:
        await select_channel_to_monitor()
        await telegram_client.run_until_disconnected()

    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    
if __name__ == '__main__':
    asyncio.run(main())