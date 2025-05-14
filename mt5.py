import MetaTrader5 as mt5
from flask import Flask, request, jsonify
import asyncio
import pprint
app = Flask(__name__)

if not mt5.initialize():
    print("initialize() failed")
    mt5.shutdown()

print(mt5.terminal_info(), end="\n\n")
print(mt5.account_info(), end="\n\n")
print(mt5.version(), end="\n\n")




@app.route('/trade_signal', methods=['POST'])
def trade_signal():
    # TODO: show me how you want the signal to look like
    signal_data = request.get_json()
    '''signal_data = {
        "symbol": "EURUSD",
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
    mt5.