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
    return mt5.ORDER_TYPE_BUY_LIMIT if direction == "BUY" else mt5.ORDER_TYPE_SELL

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
        "action": mt5.TRADE_ACTION_DEAL,
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


def handle_trade_signal(data):
    symbol = data.get("pair")
    direction = data.get("direction")
    entry = float(data.get("entry"))
    sl = float(data.get("sl", 0))
    tp1 = float(data.get("tp1", 0))

    if not all([symbol, direction, entry]):
        logger.warning("Missing trade data. Aborting.")
        return None

    initialize_mt5()
    order_id = send_order(symbol, direction, entry, sl, tp1)
    shutdown_mt5()
    return order_id


if __name__ == '__main__':
    data = {
        "pair": "EURUSD",
        "direction": "BUY",
        "entry": 1.08500,
        "sl": 1.08000,
        "tp1": 1.09000
        }

    handle_trade_signal(data)

