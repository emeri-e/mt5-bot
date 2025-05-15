import MetaTrader5 as mt5
from flask import Flask, request, jsonify
import asyncio
import pprint
app = Flask(__name__)


if not mt5.initialize():
    print("initialize() failed")
    mt5.shutdown()

symbol = 'EURUSD'
symbol_info = mt5.symbol_info(symbol)
if symbol_info is None:
    print(f"Symbol {symbol} not found")
    mt5.shutdown()

if not symbol_info.visible:
    print(f"Symbol {symbol} not visible, trying to add it")
    if not mt5.symbol_select(symbol, True):
        print(f"symbol_select({symbol}) failed")
        mt5.shutdown()

print(mt5.terminal_info(), end="\n\n")
print(mt5.account_info(), end="\n\n")
print(mt5.version(), end="\n\n")




@app.route('/trade_signal', methods=['POST'])
def trade_signal():
    # TODO: show me how you want the signal to look like
    signal_data = request.get_json()
    '''signal_data = {
        "symbol": "USDEUR",
        "action": "buy",
        "lot": 0.1,
        "take_profit": 1.2000,
        "stop_loss": 1.1900
    }'''
    print(f"Received signal: {signal_data}")
    return jsonify({"status": "received"}), 200


# if __name__ == '__main__':
#     app.run(port=1960)

def test_trade_signal():
    lot = 0.1
    point = mt5.symbol_info(symbol).point
    price = mt5.symbol_info_tick(symbol).ask
    deviation = 20
    # signal_data = {
    #     "action": mt5.TRADE_ACTION_DEAL,
    #     "symbol": symbol,
    #     "volume": lot,
    #     "type": mt5.ORDER_TYPE_BUY,
    #     "price": price,
    #     "sl": price - 100 * point,
    #     "tp": price + 100 * point,
    #     "deviation": deviation,
    #     "magic": 234000,
    #     "comment": "python script open",
    #     "type_time": mt5.ORDER_TIME_GTC,
    #     "type_filling": mt5.ORDER_FILLING_RETURN,
    # }
    #price = 1.1950
    signal_data = {
        "symbol": symbol,
        "action": mt5.TRADE_ACTION_DEAL,
        'price': price,
        'type_filling': mt5.ORDER_FILLING_RETURN,
        'type_time': mt5.ORDER_TIME_GTC,
        'volume': 0.1,
        "type": mt5.ORDER_TYPE_BUY,
        "tp": price + 100 * point,
        "sl": price - 100 * point,
        "comment": "Test order",
        "magic": 123456,
        "deviation": 10,
        }
    result = mt5.order_send(signal_data)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed: {result.retcode}")
        reet_code_dict = result._asdict()
        for key, value in reet_code_dict.items():
            print(f"{key}: {value}")

    else:
        print(f"Order successful: {result.retcode}")

test_trade_signal()