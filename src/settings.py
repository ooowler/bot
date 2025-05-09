import os


TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
REDIS_APP_URL = os.environ["REDIS_APP_URL"]
REDIS_FSM_URL = os.environ["REDIS_FSM_URL"]

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = os.environ["POSTGRES_PORT"]
POSTGRES_DB = os.environ["POSTGRES_DB"]

ALLOW = list(map(int, os.environ["ALLOW"].split()))

DEV_MODE = int(os.getenv("DEV_MODE", ""))
