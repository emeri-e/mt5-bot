import json
import os
from datetime import datetime
import re
from config import base

TRADE_LOG_PATH = base.TRADE_LOG_PATH


def load_trades():
    '''Loads trades from the trade.json file'''
    if not os.path.exists(TRADE_LOG_PATH):
        return {}
    with open(TRADE_LOG_PATH, "r") as f:
        return json.load(f)

def save_trades(trades):
    '''Save trade into the trade.json file'''
    with open(TRADE_LOG_PATH, "w") as f:
        json.dump(trades, f, indent=4)

def log_new_trade(message_id, signal_data):
    trades = load_trades()
    trades[message_id] = {
        "timestamp": datetime.now().isoformat(),
        "signal": signal_data,
        "status": "pending",
        "order_id": None,
        "updates": []
    }
    save_trades(trades)

def update_trade_status(message_id, order_id):
    trades = load_trades()
    if message_id in trades:
        trades[message_id]["order_id"] = order_id
        trades[message_id]["status"] = "executed"
        save_trades(trades)

def log_trade_update(reply_message_id, update_results):
    
    trades = load_trades()
    if reply_message_id in trades:
        trades[reply_message_id].setdefault("updates", []).append({
            "timestamp": datetime.now().isoformat(),
            "results": update_results  
        })
        save_trades(trades)

def get_order_id_by_message_id(message_id):
    trades = load_trades()
    trade = trades.get(message_id)
    return trade.get("order_id") if trade else None


def replace_case_insensitive(message, pattern, replacement):
    return re.sub(pattern, replacement, message, flags=re.IGNORECASE)