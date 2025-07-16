import MetaTrader5 as mt5
import logging
logger = logging.getLogger('mybot')


def get_running_orders():
    order = mt5.orders_get()
    if not order:
        order = mt5.positions_get()
    return order
def initialize_mt5(login, password, server):
    shutdown_mt5()

    if not mt5.initialize(login=login, password=password, server=server):
        logger.error(f"MT5 Initialization failed for {login}: {mt5.last_error()}")
        return False

    logger.info(f"MT5 Initialized successfully for {login}")
    return True

def shutdown_mt5():
    mt5.shutdown()
    logger.info("MT5 Shutdown.")

def get_order_type(direction):
    return mt5.ORDER_TYPE_BUY_LIMIT if direction == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT

def find_real_symbol(target):
    for sym in mt5.symbols_get():
        if sym.name.upper().startswith(target):
            return sym.name
    return None

def send_order(symbol, direction, entry_price, sl, tp, lot=0.1):
    order_type = get_order_type(direction)

    # Ensure symbol is available
    if not mt5.symbol_select(symbol, True):
        symbol = find_real_symbol(symbol)
        if not symbol:
            logger.error(f"Failed to select symbol {symbol}")
            return None
        
        print(f'Changed symbol name to {symbol}')
    point = mt5.symbol_info(symbol).point
    price = entry_price
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
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
    print("Order placed successfully!")
    return result.order

def update_trade(order_id, action):
    order = mt5.orders_get(ticket=order_id)
    if order:
        order = order[0]
        state = order.state
        if state in (mt5.ORDER_STATE_FILLED, mt5.ORDER_STATE_PARTIAL):
            order_action = mt5.TRADE_ACTION_SLTP
            position_type = 'position'
            volume = order.volume_current
        elif state == mt5.ORDER_STATE_PLACED:
            order_action = mt5.TRADE_ACTION_MODIFY
            position_type = 'order'
            volume = order.volume_current
        else:
            return False, f"unsupported order state: {state}"

    else:
        pos = mt5.positions_get(ticket=order_id)
        if not pos:
            logger.warning(f"Position {order_id} not found.")
            return False, 'ticket id not found'
        order = pos[0]
        order_action = mt5.TRADE_ACTION_SLTP
        position_type = 'position'
        volume = order.volume
 


    symbol = order.symbol
    
    price_info = mt5.symbol_info_tick(symbol)
    if price_info is None:
        logger.warning(f"Price info for {symbol} not found.")
        return False, 'no price info'

    if action["type"] == "modify_sl":
        if action["value"] == "be":
            sl = order.price_open
        else:
            sl = float(action["value"])
        
        
        request = {
            "action": order_action, #Check the order status and change to mt5.TRADE_ACTION_SLTP if necessary 
            "price" : order.price_open,
            position_type : order_id,
            "symbol": symbol,
            "sl": sl,
            "tp": order.tp,
            "type": order.type,
            "magic": order.magic,
        }
        result = mt5.order_send(request)
        status = result.retcode == mt5.TRADE_RETCODE_DONE
        return status, f'[to {action["value"]}] {result.comment}'

    elif action["type"] == "close_trade":
        if position_type == 'position':
            close_type = mt5.ORDER_TYPE_SELL if order.type == 0 else mt5.ORDER_TYPE_BUY
            price = price_info.bid if order.type == 0 else price_info.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": order_id,
                "symbol": symbol,
                "volume": volume,
                "type": close_type,
                "price": price,
                "deviation": 10,
                "magic": order.magic,
            }
        elif position_type == 'order':
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order_id,
                "symbol": symbol,
                "magic": order.magic,
            }
        
        else:
            return False, 'unkwown state'

        result = mt5.order_send(request)
        status = result.retcode == mt5.TRADE_RETCODE_DONE
        return status, f'[trade close] {result.comment}'
    elif action["type"] == 'change_entry':
        #change entry
        entry = float(action["value"])
        if position_type == 'order':

            request = {
                "action": mt5.TRADE_ACTION_MODIFY, #Check the order status and change to mt5.TRADE_ACTION_SLTP if necessary 
                "order" : order_id,
                "symbol": symbol,
                "price" : entry,
                'sl' : order.sl,
                'tp' : order.tp,
                "type": order.type,
                "type_time": order.type_time,
                "type_filling": order.type_filling,
            }
            result = mt5.order_send(request)
            status = result.retcode == mt5.TRADE_RETCODE_DONE
            return status, f'[to {action["value"]}] {result.comment}'
        else:
            logger.debug('order has already been filled')
            return False, 'order already filled'

    elif action["type"] == "tp_hit":
        logger.debug(f"Take-profit level hit: TP{action.get('tp', '')} for order {order_id}")
        return True, 'tp-hit'
    
    elif action['type'] == 'change_tp':
        
        tp = float(action["value"])
        
        request = {
            "action": order_action, #Check the order status and change to mt5.TRADE_ACTION_SLTP if necessary 
            "price" : order.price_open,
            position_type : order_id,
            "symbol": symbol,
            "sl": order.sl,
            "tp": tp,
            "type": order.type,
            "magic": order.magic,
        }
        result = mt5.order_send(request)
        status = result.retcode == mt5.TRADE_RETCODE_DONE
        return status, f'[to {action["value"]}] {result.comment}'
    elif action["type"] == "note":
        logger.debug(f"Note update: {action['text']} for order {order_id}")
        return True, 'noted'

    logger.warning(f"Unknown action type: {action}")
    return False, 'unknown update action type'


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
def handler(data, login=None, password=None, server=None):
    msg_type = data.get("type")
    order_id = data.get("order_id")

    if not (login and password and server):
        return {"error": "Missing login credentials"}

    if msg_type == "new":
        signal_data = data.get("data")
        if not signal_data:
            return {"error": "Missing signal data"}

        if not initialize_mt5(login=int(login), password=password, server=server):
            return {"error": "Failed to initialize MT5"}

        new_order_id = send_order(
            symbol=signal_data.get("pair"),
            direction=signal_data.get("direction"),
            entry_price=float(signal_data.get("entry")),
            sl=float(signal_data.get("sl", 0)),
            tp=float(signal_data.get("tp", 0)),
            lot=float(signal_data.get("lot", 0))
        )
        shutdown_mt5()
        return {"order_id": new_order_id}

    elif msg_type == "update":
        actions = data["data"].get("actions")
        if not actions or not order_id:
            return {"error": "Invalid update format"}

        if not initialize_mt5(login=int(login), password=password, server=server):
            return {"error": "Failed to initialize MT5"}

        results = []
        for action in actions:
            success, comment = update_trade(order_id, action)
            results.append({"action": action["type"], "success": success, 'comment': comment})
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