import asyncio
import json
import os
import sys
import requests
from telethon import TelegramClient, events
import logging
import re
from config import base
from functions import get_order_id_by_message_id, load_accounts, log_new_trade, log_trade_update, save_accounts, update_trade_status, load_trades, hash_signal

import tkinter as tk
from tkinter import messagebox, ttk

from collections import defaultdict, deque
from datetime import datetime, timedelta

# message_buffer[chat_id] = deque of recent messages (max 10, or 3-5 minutes)
message_buffer = defaultdict(lambda: deque(maxlen=10))

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
logger.setLevel(logging.INFO)

from parser import call_ai_parser
from mt5.utils import handler as h, get_running_orders#type: debug

# === Telegram API Setup ===
api_id = base.api_id
api_hash = base.api_hash
session_file = 'user'
telegram_client = TelegramClient(session_file, api_id, api_hash)

LOT_SIZE = base.lot_size
TP_INDEX = base.tp_index

async def tg_log(text, edited=False):
    bot = app.bot
    if not edited:
        await bot.send_message(chat_id='-1002802602094', text=text)

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
            entries.remove((frame, lot_var, tp_var, login_var, password_var, server_var, username_var, partial_index_var, partial_percent_var))
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


def parse_trade_signal(text: str):
    try:
        response = call_ai_parser(text)
        # parsed = json.loads(response)
        if response.get("type") == "new":
            return {k: v for k, v in response.items() if k != "type"}
    except Exception as e:
        print(f"parse_trade_signal failed: {e}")
    return None

def parse_update_instruction(text: str):
    try:
        response = call_ai_parser(text)
        # parsed = json.loads(response)
        if response.get("type") == "update":
            return response.get("actions", [])
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
    telegram_client.add_event_handler(edited_handler, events.MessageEdited(chats=selected_channel))
    print(f"Monitoring started for: {selected_channel.name} (ID: {selected_channel.entity.id})")


async def message_handler(event, edited=False):
    if not event.message.text:
        return
    try:
        await tg_log(event.message.text, edited=edited)
    except Exception as e:
        logger.warning(f"failed to send log to telegram: {e}")

    telegram_message = event.message.text
    message_id = str(event.message.id)
    chat_id = event.chat_id
    # print(message_id)
    # return

    trades = load_trades('general')
    if message_id in trades:
        logger.info('this signal id is already traded')
        return

    if not message_buffer.get(chat_id):
        message_buffer[chat_id] = deque([])

    message_buffer[chat_id].append({
        "id": message_id,
        "text": telegram_message,
        "timestamp": datetime.now(),
    })

    now = datetime.now()
    message_buffer[chat_id] = deque([
        msg for msg in message_buffer[chat_id]
        if now - msg["timestamp"] < timedelta(minutes=2)
    ])

    logger.info(message_buffer[chat_id])

    combined_text = "\n".join([msg["text"] for msg in message_buffer[chat_id]])

    if is_new_trade_message(telegram_message):
        signal_data = parse_trade_signal(telegram_message)
        if signal_data.get('pair') and signal_data.get('direction') and signal_data.get('entry') and signal_data.get('sl') and signal_data.get('tp1'):
            pass
        else:
            logger.info('invalid or incomplete signal info')
            return
            # logger.info(f'Retrying with combined text: {combined_text}')
            # signal_data = parse_trade_signal(combined_text)
        if not signal_data:
            return

        signal_hash = hash_signal(signal_data)
        for msg_id,trade in trades.items():
            if trade.get('hash') == signal_hash:
                logger.info('This signal hash already exists')
                return
        signal_data['hash'] = signal_hash
        log_new_trade('general', message_id, signal_data)

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


# @telegram_client.on(events.MessageEdited)
async def edited_handler(event):
    # import pdb
    # pdb.set_trace()

    logger.info('An EDITED message recieved')
    await message_handler(event, edited=True)


async def main():
    from interface import create_bot_app

    global ACCOUNTS
    show_accounts_settings_window()
    ACCOUNTS = load_accounts()

    global app
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
    