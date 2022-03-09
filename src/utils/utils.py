import logging
import sys
import re
import requests
import json
from consts import SLACK_WEBHOOK

def get_logger():
    frmtr = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    hndlr = logging.StreamHandler(sys.stdout)
    hndlr.setFormatter(frmtr)
    logger = logging.getLogger(__name__)
    logger.addHandler(hndlr)
    logger.setLevel(logging.DEBUG)
    return logger

logger = get_logger()

def send_alert(message):
    message = f"*{'ALERT FROM VIDEO-TEXT-DETECTION REPO'}*\n{message}"
    payload = {"text": message}
    requests.post(url=SLACK_WEBHOOK, data=json.dumps(payload))

def custom_json_deserializer(v):
    if v is None:
        return
    try:
        return json.loads(v.decode('utf-8'))
    except json.decoder.JSONDecodeError:
        logger.exception('Unable to decode: %s', v)
        return None