import numpy as np
import imutils
import math
import cv2

from utils.drawing import draw_polygon
from utils.helpers import clip_value, calculate_centroid


def __extract_corners(gray_image, base):
    hull = cv2.convexHull(base)
    epsl = 0.07 * cv2.arcLength(base, True)
    hull = cv2.approxPolyDP(hull, epsl, True)
    hull = np.float32(hull)

    method = cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT
    criteria = (method, 1000, 1e-4)
    cv2.cornerSubPix(gray_image, hull, (5, 5), (-1, -1), criteria)
    
    corners = [pt[0] for pt in hull]
       # OBJECTIVE: Find top-right corner and use to label corners
       # Note: currently all corners are in CW order
       # Note: ordering will be checked below against expected corners
    
    if len(corners) < 4:
        return (False, None)

    tr_idx = np.argmin(c[0] + c[1] for c in corners)
    tl = corners[tr_idx]
    bl = corners[(tr_idx - 1) % 4]
    br = corners[(tr_idx - 2) % 4]
    tr = corners[(tr_idx - 3) % 4]
    
    # reformat and ensure that ordering is as expected below
    return (True, np.float32([[c[0], c[1]] for c in [tl, bl, br, tr]]))


def __extract_contours(binary_image):
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL,
                        cv2.CHAIN_APPROX_NONE)
    if len(contours) < 1:
        return (False, None)
    
    return (True, max(contours, key=cv2.contourArea))


def __associate(roi, box, corners):
    w0 = max(abs(corners[2][0] - corners[3][0]), 
             abs(corners[1][0] - corners[0][0]))  
    w1 = max(abs(corners[2][0] - corners[1][0]), 
             abs(corners[3][0] - corners[0][0])) 

    if w0 >= w1:
        do_flip = True
        w = h = w0
    else:
        do_flip = False
        w = h = w1

    corners_pp = np.float32([[0, 0], [0, h], [w, h], [w, 0]])
    homogrm, _ = cv2.findHomography(corners, corners_pp)

    subject = cv2.warpPerspective(roi, homogrm, (int(math.ceil(w)), int(math.ceil(h))))
    if do_flip:
        subject = cv2.flip(subject, -1)
    
    transfered = np.float32(
        [
            [corners[0][0] + box[0], corners[0][1] + box[1]],
            [corners[1][0] + box[0], corners[1][1] + box[1]],
            [corners[2][0] + box[0], corners[2][1] + box[1]],
            [corners[3][0] + box[0], corners[3][1] + box[1]]
        ]
    )

    return (w, subject, transfered)


def __locate(contour):
    # print(contours)
    #cnt = imutils.grab_contours(contours[0])
    M = cv2.moments(contour)
    if M['m00'] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
    else:
        return (0,0)
    return (cx, cy)


def unpack_fingerprint(source_image):
    """ Decodes and returns the encoded IDs present on the landing pad """
    aruco_dist = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
    aruco_prms = cv2.aruco.DetectorParameters_create()
    aruco_prms.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

    _, ids, _ = cv2.aruco.detectMarkers(source_image, aruco_dist,
                            parameters=aruco_prms)

    return [] if ids is None else ids


def unpack_scene(source_image, bbox, debug=False):
    box = [clip_value(bbox[0], 0), clip_value(bbox[1], 0),
           clip_value(bbox[2], 0), clip_value(bbox[3], 0)]
    
    roi = source_image[box[1]:box[1] + (box[3] - box[1]), 
                       box[0]:box[0] + (box[2] - box[0])]

    gray_image = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray_gblur = cv2.GaussianBlur(gray_image, (15, 15), 0)
    
    T, _ = cv2.threshold(gray_gblur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    b_image = cv2.Canny(gray_image, 0.82 * T, T)
    b_image = cv2.morphologyEx(b_image, cv2.MORPH_CLOSE, 
               np.ones((1, 1), np.uint8), iterations=10)

    ret, base_contour = __extract_contours(b_image)
    if not ret:
        return (source_image, None, None, None)
    
    ret, corners = __extract_corners(gray_gblur, base=base_contour)
    if not ret:
        return (source_image, None, None, None)
    
    dim0, subject, corners = __associate(roi, box, corners)
    center_point = calculate_centroid(base_contour)
    
    if debug:
        source_image = draw_polygon(source_image, corners, 
                        [(0, 0, 255)] * 4)
        cv2.circle(source_image, center, 7, (255, 255, 255), -1) 
    
    return (source_image, subject, dim0, center_point)
