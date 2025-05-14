import MetaTrader5 as mt5
#TRADE_ACTION_PENDING(Place an order at a specified price)
signal_data = {
    "symbol": "EURUSD",
    "action": mt5.TRADE_ACTION_PENDING,
    'price': 1.1950,
    'type_filling': mt5.ORDER_FILLING_FOK,
    'type_time': mt5.ORDER_TIME_GTC,
    'volume': 0.1,
    "take_profit": 1.2000,
    "stop_loss": 1.1900,
    "comment": "Test order",
    "magic": 123456,
    "deviation": 10,

}