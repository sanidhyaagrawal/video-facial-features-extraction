import cv2
import numpy as np
import time
import math

from typing import Tuple, List
from collections import Counter

# local imports
from src.models.skin_tone import SkinToneDetection
from consts import INSIGHTFACE_MODEL_URL
# FaceAnalysis [Age & Gender]
import insightface
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image

# FaceRecognition & Encoding
import face_recognition

insightface.utils.storage.BASE_REPO_URL = INSIGHTFACE_MODEL_URL

class FeatureExtraction:
    def __init__(self) -> None:
        self.face_analysis = FaceAnalysis(
            allowed_modules=['detection', 'genderage'])
        self.face_analysis.prepare(ctx_id=0, det_size=(640, 640))

    def get_faces_raw_info(self, merged_frames_list: List[np.ndarray]) -> Tuple[List[np.ndarray], List[np.ndarray], List[np.ndarray]]:
        faces_details = []
        locations = []
        encodings = []
        face_crops = []
        for merged_frame in merged_frames_list:
            # print(merged_frame.shape)
            h, w, _ = merged_frame.shape
            area = (h * w)/10000
            f = -0.0001*area + 0.75
            if f > 1:
                f = 1
            elif f < 0:
                f = 0.2
            merged_frame = cv2.resize(merged_frame, (0, 0), fx=f, fy=f)
            # print(merged_frame.shape)

            t1 = time.time()
            faces_details += self.face_analysis.get(merged_frame)
            _face_locations = face_recognition.face_locations(merged_frame)
            locations += _face_locations
            encodings += face_recognition.face_encodings(
                merged_frame, known_face_locations=_face_locations)

            for location in _face_locations:
                face_crop = merged_frame[location[0]:location[2], location[3]:location[1]]
                face_crops.append(face_crop)

            print("Time Taken:", time.time()-t1)

        return faces_details, locations, encodings, face_crops

    def calc_distance(self, center_cord, faces_details):
        """
        Pair face encodeing from 'face_recognition' with face details from 'insightface' based on location
        """
        p0, p1 = center_cord
        dist = []
        min_dist = 10000
        for face_detail in faces_details:
            box = face_detail['bbox']
            box[1], box[0], box[3], box[2] = box[0], box[1], box[2], box[3]
            s0, s1 = (int(box[1] + box[3])//2, int(box[0] + box[2])//2)
            # Edit this line to [0]s and [1]s
            dist_ = math.sqrt(abs(p0 - s0)**2 + abs(p1 - s1)**2)
            if dist_ < min_dist:
                min_dist = dist_
                min_dist_detail = face_detail
            dist.append(dist_)  # Save data to list
        return min_dist_detail

    def merge_info(self, faces_details, locations, encodings, face_crops):
        merged_info = []
        for i in range(len(locations)):
            box = locations[i]
            center_cord = (int(box[1] + box[3])//2, int(box[0] + box[2])//2)
            info = self.calc_distance(center_cord, faces_details)
            merged_info.append(
                {'location': box, 'encoding': encodings[i], 'face_crop': face_crops[i], 'gender': info['gender'], 'age': info['age']})
        return merged_info

    def cluster_faces(self, encodings):
        clusters = []
        tolerance = 0.6  # lower value --> less matches (more clusters)
        remaining = [0]
        all_used = []
        while len(remaining) > 0:
            enc1 = encodings[remaining[0]]  # get first encoding of remaining
            compare_faces = np.array(face_recognition.api.compare_faces(
                encodings, enc1, tolerance=tolerance))
            matching = np.where(compare_faces == True)[0].tolist()
            remaining = np.where(compare_faces == False)[0].tolist()
            for m in matching:
                encodings[m] = np.full((128), np.inf)
            clusters.append(matching)
            all_used.extend(matching)
            remaining = list(set(remaining) - set(all_used))

        # remove clusters with less than 5 faces
        clusters = [cluster for cluster in clusters if len(cluster) > 5]
        return clusters

    def aggregate_cluster_info(self, clusters, merged_info):
        info_clusters = {}
        for cluster_index in range(len(clusters)):
            info_clusters[cluster_index] = {
                'gender': [], 'age': [], 'skin_tone': [], 'locations': [], 'encodings': [], 'face_crops': []}
            for i in clusters[cluster_index]:
                info_clusters[cluster_index]['locations'].append(
                    merged_info[i]['location'])
                info_clusters[cluster_index]['encodings'].append(
                    merged_info[i]['encoding'])
                info_clusters[cluster_index]['gender'].append(
                    merged_info[i]['gender'])
                info_clusters[cluster_index]['age'].append(
                    merged_info[i]['age'])
                info_clusters[cluster_index]['face_crops'].append(
                    merged_info[i]['face_crop'])
                is_valid, skin_tone = SkinToneDetection(
                ).img2skintone(merged_info[i]['face_crop'])
                if is_valid:
                    info_clusters[cluster_index]['skin_tone'].append(skin_tone)

            info_clusters[cluster_index]['count'] = len(
                info_clusters[cluster_index]['age'])

        for index_key in info_clusters.keys():
            for attribute_key in ['gender', 'age']:
                info_clusters[index_key][attribute_key] = np.median(
                    info_clusters[index_key][attribute_key])
            # info_clusters[index_key]['skin_tone'] = Counter(info_clusters[index_key]['skin_tone']).most_common(1)[0][0]
            info_clusters[index_key]['skin_tone'] = np.mean(
                info_clusters[index_key]['skin_tone'])

        return info_clusters

    def get_features(self, merged_frames_list: List[np.ndarray]):
        faces_details, locations, encodings, face_crop = self.get_faces_raw_info(
            merged_frames_list)

        if len(locations) > 0 and len(faces_details) > 0:
            merged_info = self.merge_info(
                faces_details, locations, encodings, face_crop)
            faces_clusters = self.cluster_faces(encodings)
            info_clusters = self.aggregate_cluster_info(
                faces_clusters, merged_info)
            if len(info_clusters) > 0:
                # keys = ['gender', 'age', 'skin_tone', 'locations', 'encodings', 'face_crops']
                return True, info_clusters
            else:
                return False, None
        else:
            return False, None
