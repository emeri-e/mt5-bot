import MetaTrader5 as mt5
import logging
logger = logging.getLogger(__name__)

def initialize_mt5():
    if not mt5.initialize():
        logger.error(f"MT5 Initialization failed: {mt5.last_error()}")
        return False
    logger.info("MT5 Initialized successfully.")
    return True

def shutdown_mt5():
    mt5.shutdown()
    logger.info("MT5 Shutdown.")

def get_order_type(direction):
    return mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

def send_order(symbol, direction, entry_price, sl, tp):
    lot = 0.1  
    order_type = get_order_type(direction)

    # Ensure symbol is available
    if not mt5.symbol_select(symbol, True):
        logger.error(f"Failed to select symbol {symbol}")
        return None
    point = mt5.symbol_info(symbol).point
    price = entry_price
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": price - 100 * point,
        "tp": price + 100 * point,
        "deviation": 10,
        "magic": 234000,  
        "comment": "Auto Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Order send failed: {result.retcode} - {result.comment}")
        return None

    logger.info(f"Order placed successfully: {result}")
    return result.order

def update_trade(order_id, action):
    order = mt5.history_orders_get(ticket=order_id)
    if not order:
        logging.warning(f"Position {order_id} not found.")
        return False
    order = order[0]
    print(order)
    logging.info(order)


    symbol = order.symbol
    volume = order.volume
    price_info = mt5.symbol_info_tick(symbol)
    if price_info is None:
        logging.warning(f"Price info for {symbol} not found.")
        return False

    if action["type"] == "modify_sl":
        if action["value"] == "be":
            sl = order.price_open
        else:
            sl = float(action["value"])

        request = {
            "action": mt5.TRADE_ACTION_SLTP, #Check the order status and change to mt5.TRADE_ACTION_SLTP if necessary 
            "position": order_id,
            "symbol": symbol,
            "sl": sl,
            "tp": order.tp,
            "type": mt5.ORDER_TYPE_BUY if order.type == 0 else mt5.ORDER_TYPE_SELL,
            "magic": order.magic,
        }
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    elif action["type"] == "close_trade":
        close_type = mt5.ORDER_TYPE_SELL if order.type == 0 else mt5.ORDER_TYPE_BUY
        price = price_info.bid if order.type == 0 else price_info.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL if order.state == mt5.ORDER_STATE_FILLED else mt5.TRADE_ACTION_MODIFY, #find if the order is pending or running and act accordinly
            "position": order_id,
            "symbol": symbol,
            "volume": volume,
            "type": close_type,
            "price": price,
            "deviation": 10,
            "magic": order.magic,
        }
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE
    elif action["type"] == 'change_entry':
        #change entry
        pass
    elif action["type"] == "tp_hit":
        logging.info(f"Take-profit level hit: TP{action.get('tp', '')} for order {order_id}")
        return True

    elif action["type"] == "note":
        logging.info(f"Note update: {action['text']} for order {order_id}")
        return True

    logging.warning(f"Unknown action type: {action}")
    return False


# def handle_trade_signal(data):
#     symbol = data.get("pair")
#     direction = data.get("direction")
#     entry = float(data.get("entry"))
#     sl = float(data.get("sl", 0))
#     tp1 = float(data.get("tp1", 0))

#     if not all([symbol, direction, entry]):
#         logger.warning("Missing trade data. Aborting.")
#         return None

#     initialize_mt5()
#     order_id = send_order(symbol, direction, entry, sl, tp1)
#     shutdown_mt5()
#     return order_id
def handler(data):
    msg_type = data.get("type")
    order_id = data.get("order_id")

    if msg_type == "new":
        signal_data = data.get("data")
        if not signal_data:
            return {"error": "Missing signal data"}

        initialize_mt5()
        new_order_id = send_order(
            symbol=signal_data.get("pair"),
            direction=signal_data.get("direction"),
            entry_price=float(signal_data.get("entry")),
            sl=float(signal_data.get("sl", 0)),
            tp=float(signal_data.get("tp1", 0))
        )
        shutdown_mt5()
        return {"order_id": new_order_id}

    elif msg_type == "update":
        actions = data["data"].get("actions")
        if not actions or not order_id:
            return {"error": "Invalid update format"}

        initialize_mt5()
        results = []
        for action in actions:
            success = update_trade(order_id, action)
            results.append({"action": action["type"], "success": success})
        shutdown_mt5()
        return {"status": "processed", "results": results}

    else:
        return {"error": f"Unknown message type: {msg_type}"}


if __name__ == '__main__':
    data = {
        "pair": "EURUSD",
        "direction": "BUY",
        "entry": 1.08500,
        "sl": 1.08000,
        "tp1": 1.09000
        }

    # handle_trade_signal(data)