import MetaTrader5 as mt5
from flask import Flask, request, jsonify
import asyncio

app = Flask(__name__)

mt5.initialize()

@app.route('/trade_signal', methods=['POST'])
def trade_signal():
    # TODO: show me how you want the signal to look like
    signal_data = request.get_json()
    print(f"Received signal: {signal_data}")
    return jsonify({"status": "received"}), 200


if __name__ == '__main__':
    app.run(port=1960) 
