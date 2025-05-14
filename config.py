from decouple import config

class BaseConfig:
    api_id = config('API_ID')
    api_hash = config('API_HASH')


base = BaseConfig()