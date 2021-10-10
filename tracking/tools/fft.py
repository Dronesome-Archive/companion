import numpy as np

from math import ceil
from cv2 import cv2


def fftd(image, backwards=False):
    return cv2.dft(np.float32(image), flags=((cv2.DFT_INVERSE | cv2.DFT_SCALE) if backwards else cv2.DFT_COMPLEX_OUTPUT))


def real(image):
	return image[:, :, 0]


def imag(image):
	return image[:, :, 1]


def complex_multiplication(a, b):
    x = np.zeros(a.shape, a.dtype)

    x[:, :, 0] = a[:, :, 0] * b[:, :, 0] - a[:, :, 1] * b[:, :, 1]
    x[:, :, 1] = a[:, :, 0] * b[:, :, 1] + a[:, :, 1] * b[:, :, 0]
    
    return x


def complex_division(a, b):
    x = np.zeros(a.shape, a.dtype)
    divisor = 1. / (b[:, :, 0] ** 2 + b[:, :, 1] ** 2)

    x[:, :, 0] = (a[:, :, 0] * b[:, :, 0] + a[:, :, 1] * b[:, :, 1]) * divisor
    x[:, :, 1] = (a[:, :, 1] * b[:, :, 0] + a[:, :, 0] * b[:, :, 1]) * divisor
    
    return x


def rearrange(image):
    assert(image.ndim == 2)
       
    _image = np.zeros(image.shape, image.dtype)
    xh, yh = ceil(image.shape[1] / 2), ceil(image.shape[0] / 2)

    _image[0: yh, 0: xh] = image[yh: image.shape[0], xh: image.shape[1]]
    _image[yh: image.shape[0], xh: image.shape[1]] = image[0: yh, 0: xh]
    _image[0: yh, xh: image.shape[1]] = image[yh: image.shape[0], 0: xh]
    _image[yh: image.shape[0], 0: xh] = image[0: yh, xh: image.shape[1]]

    return _image