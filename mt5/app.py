from flask import Flask, request, jsonify
from utils import handle_trade_signal
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return "MT5 Trade API is running."

@app.route('/signal', methods=['POST'])
def receive_trade_signal():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_keys = ["pair", "direction", "entry"]
        if not all(key in data for key in required_keys):
            return jsonify({"error": f"Missing required keys: {required_keys}"}), 400

        order_id = handle_trade_signal(data)
        if order_id is None:
            return jsonify({"error": "Failed to place order"}), 500

        return jsonify({"message": "Order placed successfully", "order_id": order_id})

    except Exception as e:
        logging.exception("Error processing trade signal")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
