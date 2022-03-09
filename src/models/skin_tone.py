import cv2
import numpy as np
from typing import Tuple


class SkinToneDetection():
    """
    Class to detect skin tone in an image.
    """

    def filter_face(self, img: np.ndarray) -> np.ndarray:
        # converting from gbr to hsv color space
        img_HSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # skin color range for hsv color space
        HSV_mask = cv2.inRange(img_HSV, (0, 10, 40), (255, 210, 255))
        HSV_mask = cv2.morphologyEx(
            HSV_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        # converting from gbr to YCbCr color space
        img_YCrCb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        # skin color range for hsv color space
        YCrCb_mask = cv2.inRange(img_YCrCb, (40, 120, 60), (240, 180, 140))
        YCrCb_mask = cv2.morphologyEx(
            YCrCb_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        # find common part of skin detection (YCbCr and hsv)
        global_mask = cv2.bitwise_and(YCrCb_mask, HSV_mask)
        global_mask = cv2.medianBlur(global_mask, 3)
        global_mask = cv2.morphologyEx(
            global_mask, cv2.MORPH_OPEN, np.ones((4, 4), np.uint8))
        frame_denoised = cv2.bitwise_and(img, img, mask=global_mask)
        return frame_denoised

    def rgb2lab(self, inputColor: Tuple[int, int, int]) -> Tuple[int, int, int]:
        num = 0
        RGB = [0, 0, 0]

        for value in inputColor:
            value = float(value) / 255

            if value > 0.04045:
                value = ((value + 0.055) / 1.055) ** 2.4
            else:
                value = value / 12.92

            RGB[num] = value * 100
            num = num + 1

        XYZ = [0, 0, 0, ]

        X = RGB[0] * 0.4124 + RGB[1] * 0.3576 + RGB[2] * 0.1805
        Y = RGB[0] * 0.2126 + RGB[1] * 0.7152 + RGB[2] * 0.0722
        Z = RGB[0] * 0.0193 + RGB[1] * 0.1192 + RGB[2] * 0.9505
        XYZ[0] = round(X, 4)
        XYZ[1] = round(Y, 4)
        XYZ[2] = round(Z, 4)

        # ref_X =  95.047   Observer= 2°, Illuminant= D65
        XYZ[0] = float(XYZ[0]) / 95.047
        XYZ[1] = float(XYZ[1]) / 100.0          # ref_Y = 100.000
        XYZ[2] = float(XYZ[2]) / 108.883        # ref_Z = 108.883

        num = 0
        for value in XYZ:

            if value > 0.008856:
                value = value ** (0.3333333333333333)
            else:
                value = (7.787 * value) + (16 / 116)

            XYZ[num] = value
            num = num + 1

        Lab = [0, 0, 0]

        L = (116 * XYZ[1]) - 16
        a = 500 * (XYZ[0] - XYZ[1])
        b = 200 * (XYZ[1] - XYZ[2])

        Lab[0] = round(L, 4)
        Lab[1] = round(a, 4)
        Lab[2] = round(b, 4)

        return Lab

    def lab2skintone(self, l: int, a: int, b: int) -> Tuple[bool, str]:
        if l < 45:
            skinColour = 1  # "DUSKY"
        elif l < 55:
            if a > 9 and b > 6 and b < 20:
                skinColour = 3  # "WHEATISH-DUSKY"
            else:
                skinColour = 2  # "DUSKY-WHEATISH"
        elif l > 65:
            if a < 15 and b < 18 and b > 1:
                skinColour = 8  # "VERY FAIR"
            elif a > 20 and b > 25:
                skinColour = 6  # "FAIR-WHEATISH"
            else:
                skinColour = 5  # "WHEATISH-FAIR"
        else:

            if a < 15 and b > 13 and b < 20:
                skinColour = 7  # "FAIR"
            else:
                skinColour = 4  # "WHEATISH"
        return True, skinColour

    def img2skintone(self, face_img: np.ndarray) -> Tuple[bool, str]:
        image_filtered = self.filter_face(face_img)

        b, g, r = cv2.split(image_filtered)
        if (np.count_nonzero(r)/np.size(r))*100 < 30:  # information threshold
            return False, None

        r_mean = r[np.nonzero(r)].mean()
        g_mean = g[np.nonzero(g)].mean()
        b_mean = b[np.nonzero(b)].mean()
        rgb_mean = (r_mean, g_mean, b_mean)

        l, a, b = self.rgb2lab(rgb_mean)
        is_skin, skin_tone = self.lab2skintone(l, a, b)

        return is_skin, skin_tone
