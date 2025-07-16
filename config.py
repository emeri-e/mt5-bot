import functools
import threading
from decouple import config

class BaseConfig:
    api_id = config('API_ID')
    api_hash = config('API_HASH')
    
    BOT_TOKEN = config('BOT_TOKEN')

    GEMINI_API_KEY=config('GEMINI_API_KEY')
    OPENAI_API_KEY=config('OPENAI_API_KEY')
    SELECTED_CHANNEL = config('DEFAULT_CHANNEL')

    TRADE_LOG_PATH="trades.json"
    TRADE_LOG_DIR = "trades"
    POPULAR_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'NZD', 'CHF', 'CAD', 'XAU', 'XAG', 'BTC', 'ETH']

    lot_size=0.1
    tp_index=4
    
    mt5_lock = threading.RLock()

    def mt5_locked(cls,func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with cls.mt5_lock:
                return func(*args, **kwargs)
        return wrapper
    
base = BaseConfig()