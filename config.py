from decouple import config

class BaseConfig:
    api_id = config('API_ID')
    api_hash = config('API_HASH')

    GEMINI_API_KEY=config('GEMINI_API_KEY')
    SELECTED_CHANNEL = config('DEFAULT_CHANNEL')

    TRADE_LOG_PATH="trades.json"
    POPULAR_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'NZD', 'CHF', 'CAD', 'XAU', 'XAG', 'BTC', 'ETH']

    lot_size=0.1
    tp=1
    
base = BaseConfig()