import numpy as np

from cv2 import cv2
from math import ceil


def extract_landing_pad(image, bbox):
    roi = image[bbox[0][1]:bbox[0][1] + bbox[0][3], bbox[0][0]:bbox[0][0] + bbox[0][3]]
    gry = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # get binary thresholding of image 
    smooth = cv2.GaussianBlur(gry, (15, 15), 0)
    _, binary = cv2.threshold(smooth, 170, 255, cv2.THRESH_BINARY)

    # morphological closing
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=10)

    # Find corners:
    # 1) find the largest (area) contour in image (after thresholding)
    # 2) get contours convex hull,
    # 3) reduce degree of convex hull with Douglas-Peucker algorithm,
    # 4) refine corners with subpixel corner finder

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_contour = max(contours, key=cv2.contourArea)

    cvxhull = cv2.convexHull(max_contour)
    epsilon = 0.07 * cv2.arcLength(max_contour, True)

    cvxhull = cv2.approxPolyDP(cvxhull, epsilon, True)

    cvxhull = np.float32(cvxhull)
    method = cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT
    criteria = (method, 1e3, 1e-4)
    cv2.cornerSubPix(gry, cvxhull, (5, 5), (-1, -1), criteria)
    corners = [point[0] for point in cvxhull]

    # Find top-right corner and use it to label corners
    # Note: currently corners are in CW order
    # Note: ordering will be checked below against expected corners
    index = np.argmin(corner[0] + corner[1] for corner in corners)
    tl = corners[index]
    bl = corners[(index - 1) % 4]
    br = corners[(index - 2) % 4]
    tr = corners[(index - 3) % 4]

    # reformat and ensure that ordering is as expected below
    corners = np.float32([[corner[0], corner[1]] for corner in [tl, bl, br, tr]])

    dim_template_0 = max(abs(br[0] - tr[0]), abs(bl[0] - tl[0]))
    dim_template_1 = max(abs(br[0] - bl[0]), abs(tr[0] - tl[0]))

    if dim_template_0 >= dim_template_1:
        rot = True
        width = height = dim_template_0
    else:
        rot = False
        width = height = dim_template_1
    
    corners_pp = np.float32([[0, 0], [0, height], [width, height], [width, 0]])
    homo, mask = cv2.findHomography(corners, corners_pp)

    landing_pad = cv2.warpPerspective(roi, homo, (int(ceil(width)), int(ceil(height))))

    return landing_pad if not rot else cv2.flip(landing_pad, -1)


def extract_landing_pad_fingerprint(landing_pad):
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
    aruco_prms = cv2.aruco.DetectorParameters_create()

    (corners, ids, rejected) = cv2.aruco.detectMarkers(landing_pad, aruco_dict, parameters=aruco_prms)

    return sorted(ids) if len(ids) == 4 else []