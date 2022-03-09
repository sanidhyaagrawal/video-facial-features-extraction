import cv2
import numpy as np
from typing import Tuple, List
from consts import FRAME_EVERY_X_SECONDS

class VideoUtils():
    def __init__(self, URL: str, col_count: int = 10, row_count: int = 4) -> None:
        self.URL = URL
        self.col_count = col_count
        self.row_count = row_count
        self.max_duration = 10*60*1000  # 10 minutes
        self.frame_every_x_seconds = FRAME_EVERY_X_SECONDS
        self.success, self.frames = self.getVideoFrames()
        # print("self.success:", self.success)
        if self.success:
            self.height, self.width, _ = self.frames[-1].shape
            self.merged_frames = self.mergeFrames()
            self.same_location_thresh = self.height // 180

    def getVideoFrames(self) -> Tuple[bool, List]:
        '''
        Get list of frames from video

        return: 
            success: bool, True if frames were successfully extracted 
            frames: list, list of frames
        '''

        video = cv2.VideoCapture(self.URL)
        if not video.isOpened():
            return False, []

        currentframe = 0
        fps = int(video.get(cv2.CAP_PROP_FPS))
        frames = []
        while(video.isOpened()):
            ret, cur_frame = video.read()
            if currentframe > fps*self.max_duration:
                break
            if ret:
                if currentframe % (fps*self.frame_every_x_seconds) == 1:
                    cur_frame = cv2.copyMakeBorder(cur_frame, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=(
                        0, 255, 0))  # add border to frame
                    frames.append(cur_frame)
                currentframe += 1
            else:
                break

        video.release()

        if len(frames) > 20:
            frames = frames[:-5]  # remove last 5 frames (5 seconds)

        # add dummy frames to merged image to make number of images per row constant
        for _ in range(self.col_count - len(frames) % self.col_count):
            frames.append(frames[-1])

        return True, frames

    def mergeFrames(self) -> List:
        '''
        Merge frames into a single image

        return: 
            merged_frames: list of merged frames
        '''

        rows = []
        col_count = self.col_count
        row_count = self.row_count
        len_frames = len(self.frames)

        for i in range(col_count, len_frames+col_count, col_count):
            # stack horizontally
            rows.append(np.hstack(self.frames[i-col_count:i]))

        len_rows = len(rows)
        merged_frames = []
        # print(len_rows, row_count)
        if len_rows > row_count:
            for i in range(row_count, len_rows, row_count):
                img = np.vstack(rows[i-row_count:i])  # stack vertically
                merged_frames.append(img)

            extras = len_rows % row_count
            if extras > 0:
                img = np.vstack(rows[len_rows-extras:len_rows])
                merged_frames.append(img)
        else:
            merged_frames = rows

        return merged_frames
