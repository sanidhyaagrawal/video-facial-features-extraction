import os
from dotenv import load_dotenv
from pathlib import Path
from abc import ABC

dotenv_path = Path('/usr/app/.env.prod')
load_dotenv(dotenv_path=dotenv_path)

SENTRY_URL= os.environ.get("SENTRY_URL")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")
INSIGHTFACE_MODEL_URL = os.environ.get("INSIGHTFACE_MODEL_URL")
FRAME_EVERY_X_SECONDS = int(os.environ.get("FRAME_EVERY_X_SECONDS", 1))
S3_BASE_URL = os.environ.get("S3_BASE_URL")

class MySQLConsts(ABC):
    LOG_TABLE = os.environ.get("LOG_TABLE")

class KafkaConsts(ABC):
    GROUP_ID = os.environ.get("GROUP_ID")
    KAFKA_BROKER_URL = str(os.environ.get("KAFKA_BROKER_URL"))
    CONSUMER_TRANSACTIONS_TOPIC = str(os.environ.get("CONSUMER_TRANSACTIONS_TOPIC"))

class Status(ABC):
    PICKED = "PICKED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class ModelConsts(ABC):
    MODEL_VERSION = "1.0.0"

