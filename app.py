import cv2
import numpy as np
from typing import Tuple, List
import time 
from src.utils.utils import logger, send_alert, custom_json_deserializer

from src.utils.video_utils import VideoUtils
from src.utils.utils import custom_json_deserializer
from src.utils.db_utils import DBUtils
from src.models.features import FeatureExtraction

from kafka import KafkaConsumer, TopicPartition
from kafka.structs import OffsetAndMetadata
from consts import KafkaConsts, Status, FRAME_EVERY_X_SECONDS, SENTRY_URL, S3_BASE_URL

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


feature_extraction = FeatureExtraction()

def get_s3_url(file_name):
    return S3_BASE_URL + file_name

def get_face_features(url: str) -> Tuple[np.ndarray, np.ndarray]:
    merged_frames  = VideoUtils(url).merged_frames
    has_faces, info_clusters = feature_extraction.get_features(merged_frames)
    return has_faces, info_clusters

def thresh_skintone(score):
    if score == None:
         skin_colour = None
    elif score <= 2:
        skin_colour = 'dusky'
    elif score >= 4.5:
        skin_colour = 'fair'
    elif score >2 and score < 4.5:
        skin_colour = 'wheatish'
    else: 
        skin_colour = None
    return skin_colour

def process_result(result):
    people = []
    for i in range(len(result)):
        person = {}
        person['gender'] = result[i]['gender']
        person['age'] = result[i]['age']
        skin_tone = thresh_skintone(result[i]['skin_tone'])
        if skin_tone == None:
            person['skin_tone_score'] = None
            person['skin_tone'] = None
        else:
            person['skin_tone_score'] = result[i]['skin_tone']
            person['skin_tone'] = skin_tone
        person['duration'] = len(result[i]['locations']) * FRAME_EVERY_X_SECONDS
        people.append(person)
    return people

def process_transaction(transaction_data: dict, isRecovery: bool = False) -> None:
    """
    :param dict transaction:
    :param bool isRecovery:
    :return:
    """

    trailId = transaction_data.get("trailId", None)
    geoChatId = transaction_data.get("geoChatId", None)
    geoChatVideo = transaction_data.get("geoChatVideo", None)
    userId = transaction_data.get("userId", None)
    
    if userId is None:
        userId = DBUtils.get_userId(trailId)

    if userId == -1:
        logger.error(f"Missing userId in DB for trailId: {trailId}")
        return

    elif trailId is None or geoChatId is None or geoChatVideo is None:
        logger.error(
            f"Missing trailId, userId, geoChatId or geoChatVideo in transaction: {transaction_data}")
        return

    if isRecovery == False:
        isAlreadyProcessed = DBUtils.check_if_already_processed(geoChatId)

        if isAlreadyProcessed:
            logger.info(f"GeoChatId {geoChatId} already processed")
            return
        
        DBUtils.update_status(Status.PICKED, trailId, userId, geoChatId)
    
    file_name = geoChatVideo.split("/")[-1]
    s3_url = get_s3_url(file_name)
    
    try:
        has_faces, info_clusters = get_face_features(s3_url)
    except Exception as e:
        send_alert(f"Error in processing video: {s3_url} :: {e}")
        logger.exception(f"Error in processing video: {s3_url}")
        DBUtils.update_status(Status.FAILED, trailId, userId, geoChatId)
    else:
        if has_faces:
            people = process_result(info_clusters)
            people = sorted(people, key = lambda i: i['duration'], reverse=True)
        else:
            people = []
        DBUtils.update_trail_info(
            geoChatId, Status.SUCCESS, has_faces, people)


if __name__ == '__main__':
    if SENTRY_URL is not None:
        sentry_sdk.init(dsn=SENTRY_URL, integrations=[LoggingIntegration()]) 

    print("Conencting at - ",KafkaConsts.KAFKA_BROKER_URL)
    print("Consumer GroupId - ", KafkaConsts.GROUP_ID)
    consumer = KafkaConsumer(
        KafkaConsts.CONSUMER_TRANSACTIONS_TOPIC,
        group_id=KafkaConsts.GROUP_ID,
        bootstrap_servers=KafkaConsts.KAFKA_BROKER_URL,
        value_deserializer=custom_json_deserializer,
        auto_offset_reset='latest',
        max_poll_interval_ms=5*60*1000,
        max_poll_records=1,
        session_timeout_ms=60*1000,
        heartbeat_interval_ms=2000
    )

    for message in consumer:
        print("-----------------------------------")
        print("%s : %d ::: %d:" %
              (message.topic, message.partition, message.offset))
        print(message.value)
       
        if message.value is None:
            continue
        else:
            _val = str(message.value)
            transaction: dict = eval(_val)
        
        if transaction.get('type', None) == 'serve-ready':
            pt1 = time.time()
            process_transaction(transaction["data"])
            pt2 = time.time()
        else:
            continue
            
        print("consumer offsetting...")
        tc1 = time.time()
        tp = TopicPartition(
            KafkaConsts.CONSUMER_TRANSACTIONS_TOPIC,  message.partition)
        consumer.commit({
            tp: OffsetAndMetadata(message.offset+1, None)
        })
        tc2 = time.time()

        print(f"Time taken in process transaction = {round(pt2-pt1)} seconds")
        print(f"Time taken in committing topics   = {round(tc2-tc1)} seconds")

    
