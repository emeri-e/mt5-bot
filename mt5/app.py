from flask import Flask, request, jsonify
from utils import handle_trade_signal, handler, update_trade
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return "MT5 Trade API is running."

# @app.route('/signal', methods=['POST'])
# def receive_trade_signal():
#     try:
#         data = request.get_json()
#         if not data:
#             return jsonify({"error": "No data provided"}), 400

#         msg_type = data.get("type")
#         order_id = data.get("order_id")

#         if msg_type == "new":
#             signal_data = data.get("data")
#             if not signal_data:
#                 return jsonify({"error": "Missing signal data"}), 400
#             new_order_id = handle_trade_signal(signal_data)
#             return jsonify({"order_id": new_order_id})

#         elif msg_type == "update":
#             actions = data["data"].get("actions")
#             if not actions or not order_id:
#                 return jsonify({"error": "Invalid update format"}), 400

#             success_flags = []
#             for action in actions:
#                 result = update_trade(order_id, action)
#                 success_flags.append({"action": action["type"], "success": result})

#             return jsonify({"status": "processed", "results": success_flags})

#     except Exception as e:
#         logging.exception("Error processing trade signal")
#         return jsonify({"error": str(e)}), 500

@app.route('/signal', methods=['POST']) 
def receive_trade_signal():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        result = handler(data)
        return jsonify(result)

    except Exception as e:
        logging.exception("Error processing trade signal")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000)
