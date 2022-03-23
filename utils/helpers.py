import numpy as np
import sys

from pycoral.adapters import detect


class CALIB:
    REAL_WIDTH = 80.0
    REAL_DISTANCE = 136.0
    REFERENCE_WIDTH = 307.0


def clip_value(x, lower_bound, upper_bound=sys.maxsize):
    x = max(x, 0)
    return lower_bound if x < lower_bound else min(x, upper_bound)


def calculate_focal_length(distance, real_width, reference_width):
    return (reference_width * distance) / real_width


def calculate_distance(focal_length, real_width, reference_width):
    return (real_width * focal_length) / reference_width


def arr_to_bbox(arr):
    return detect.BBox(xmin=arr[0], ymin=arr[1], xmax=arr[2], ymax=arr[3])


def calculate_centroid(vertexes):
     _x_list = [vertex [0] for vertex in vertexes]
     _y_list = [vertex [1] for vertex in vertexes]
     _len = len(vertexes)
     _x = sum(_x_list) / _len
     _y = sum(_y_list) / _len
     return(int(_x), int(_y))
