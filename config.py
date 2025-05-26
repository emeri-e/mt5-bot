from decouple import config

class BaseConfig:
    api_id = config('API_ID')
    api_hash = config('API_HASH')

    SELECTED_CHANNEL = 'MT5 bot test'

    TRADE_LOG_PATH="trades.json"
    POPULAR_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'NZD', 'CHF', 'CAD', 'XAU', 'XAG', 'BTC', 'ETH']

base = BaseConfig()