import numpy as np
from cv2 import cv2


def x2(rect):
	return rect[0] + rect[2]


def y2(rect):
	return rect[1] + rect[3]


def limit(rect, limit):
    if rect[0] + rect[2] > limit[0] + limit[2]:
        rect[2] = limit[0] + limit[2] - rect[0]
    if rect[1] + rect[3] > limit[1] + limit[3]:
        rect[3] = limit[1] + limit[3] - rect[1]
    if rect[0] < limit[0]:
        rect[2] -= (limit[0] - rect[0])
        rect[0] = limit[0]
    if rect[1] < limit[1]:
        rect[3] -= (limit[1] - rect[1])
        rect[1] = limit[1]
    if rect[2] < 0:
        rect[2] = 0
    if rect[3] < 0:
        rect[3] = 0
    
    return rect


def get_border(original, limited):
    res = [0, 0, 0, 0]
    res[0] = limited[0] - original[0]
    res[1] = limited[1] - original[1]
    res[2] = x2(original) - x2(limited)
    res[3] = y2(original) - y2(limited)
    
    assert(np.all(np.array(res) >= 0))
    
    return res


def subwindow(image, window, border_type=cv2.BORDER_CONSTANT):
    cut_window = [x for x in window]
    limit(cut_window, [0, 0, image.shape[1], image.shape[0]])
    
    assert(cut_window[2] > 0 and cut_window[3] > 0)
    
    border = get_border(window, cut_window)
    x = image[cut_window[1]: cut_window[1] + cut_window[3], cut_window[0]: cut_window[0] + cut_window[2]]

    if(border != [0, 0, 0, 0]):
        x = cv2.copyMakeBorder(x, border[1], border[3], border[0], border[2], border_type)
    
    return x