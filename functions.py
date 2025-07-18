import json
import os
from datetime import datetime
import re
from config import base

import hashlib
import json

def hash_signal(signal: dict) -> str:
    fingerprint = json.dumps(signal, sort_keys=True)
    return hashlib.sha256(fingerprint.encode()).hexdigest()

# TRADE_LOG_PATH = base.TRADE_LOG_PATH


# def load_trades():
#     '''Loads trades from the trade.json file'''
#     if not os.path.exists(TRADE_LOG_PATH):
#         return {}
#     with open(TRADE_LOG_PATH, "r") as f:
#         return json.load(f)

# def save_trades(trades):
#     '''Save trade into the trade.json file'''
#     with open(TRADE_LOG_PATH, "w") as f:
#         json.dump(trades, f, indent=4)

# def log_new_trade(message_id, signal_data):
#     trades = load_trades()
#     trades[message_id] = {
#         "timestamp": datetime.now().isoformat(),
#         "signal": signal_data,
#         "status": "pending",
#         "order_id": None,
#         "updates": []
#     }
#     save_trades(trades)

# def update_trade_status(message_id, order_id):
#     trades = load_trades()
#     if message_id in trades:
#         trades[message_id]["order_id"] = order_id
#         trades[message_id]["status"] = "executed"
#         save_trades(trades)

# def log_trade_update(reply_message_id, update_results):
    
#     trades = load_trades()
#     if reply_message_id in trades:
#         trades[reply_message_id].setdefault("updates", []).append({
#             "timestamp": datetime.now().isoformat(),
#             "results": update_results  
#         })
#         save_trades(trades)

# def get_order_id_by_message_id(message_id):
#     trades = load_trades()
#     trade = trades.get(message_id)
#     return trade.get("order_id") if trade else None



TRADE_LOG_DIR = base.TRADE_LOG_DIR  # e.g., './trade_logs/'

DEFAULT_FILE = "accounts.json"


def get_trade_log_path(username):
    return os.path.join(TRADE_LOG_DIR, f"{username}.json")


def load_trades(username):
    path = get_trade_log_path(username)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_trades(username, trades):
    os.makedirs(TRADE_LOG_DIR, exist_ok=True)
    path = get_trade_log_path(username)
    with open(path, "w") as f:
        json.dump(trades, f, indent=4)


def log_new_trade(username, message_id, signal_data):
    trades = load_trades(username)
    trades[message_id] = {
        "timestamp": datetime.now().isoformat(),
        "signal": signal_data,
        "status": "pending",
        "order_id": None,
        "updates": []
    }
    save_trades(username, trades)


def update_trade_status(username, message_id, order_id):
    trades = load_trades(username)
    if message_id in trades:
        trades[message_id]["order_id"] = order_id
        trades[message_id]["status"] = "executed"
        save_trades(username, trades)


def log_trade_update(username, reply_message_id, update_results):
    trades = load_trades(username)
    if reply_message_id in trades:
        trades[reply_message_id].setdefault("updates", []).append({
            "timestamp": datetime.now().isoformat(),
            "results": update_results
        })
        save_trades(username, trades)


def get_order_id_by_message_id(username, message_id):
    trades = load_trades(username)
    trade = trades.get(message_id)
    return trade.get("order_id") if trade else None

def replace_case_insensitive(message, pattern, replacement):
    return re.sub(pattern, replacement, message, flags=re.IGNORECASE)


def load_accounts():
    if os.path.exists(DEFAULT_FILE):
        with open(DEFAULT_FILE, "r") as f:
            return json.load(f)
    return []

def save_accounts(accounts):
    with open(DEFAULT_FILE, "w") as f:
        json.dump(accounts, f, indent=2)

