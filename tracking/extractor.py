import numpy as np

from .utility import *
from math import ceil
from cv2 import cv2


SECTOR = 9
EPSLON = 1e-07

def get_feature_maps(image, k, mapp):
    kernel = np.array([[-1.,  0., 1.]], np.float32)
    height, width, _ = image.shape
    
    assert(image.ndim == 3 and image.shape[2])
    
    channels = 1 if image.ndim == 2 else image.shape[2]
    size_x = ceil(width / k)
    size_y = ceil(height / k)
    px = 3 * SECTOR
    op = px
    string_size = size_x * op

    if size_x % 2 != 0:
        size_x += 1
    if size_y % 2 != 0:
        size_y += 1

    mapp['size_x'] = size_x
    mapp['size_y'] = size_y
    mapp['feature_count'] = op
    mapp['feature_map'] = np.zeros((mapp['size_x'] * mapp['size_y'] * mapp['feature_count']), np.float32)

    dx = cv2.filter2D(np.float32(image), -1, kernel)
    dy = cv2.filter2D(np.float32(image), -1, kernel.T)
    arg_vector = np.arange(SECTOR + 1).astype(np.float32) * np.pi / SECTOR
    boundary_x = np.cos(arg_vector) 
    boundary_y = np.sin(arg_vector)

    r = np.zeros((height, width), np.float32)
    alfa = np.zeros((height, width, 2), np.int)
    func1(dx, dy, boundary_x, boundary_y, r, alfa, height, width, channels) 

    nearest = np.ones((k), np.int)
    nearest[0:k // 2] = -1
    
    w = np.zeros((k, 2), np.float32)
    a_x = np.concatenate((k / 2 - np.arange(k / 2) - 0.5, np.arange(k / 2, k) - k / 2 + 0.5)).astype(np.float32)
    b_x = np.concatenate((k / 2 + np.arange(k / 2) + 0.5, -np.arange(k / 2, k) + k / 2 - 0.5 + k)).astype(np.float32)
    w[:, 0] = 1.0 / a_x * ((a_x * b_x) / (a_x + b_x))
    w[:, 1] = 1.0 / b_x * ((a_x * b_x) / (a_x + b_x))

    mappmap = np.zeros(int(size_x * size_y * op), np.float32)
    func2(mappmap, boundary_x, boundary_y, r, alfa, nearest, w, k, height, width, size_x, size_y, op, string_size)
    mapp['feature_map'] = mappmap

    return mapp


def prepare(mapp, alfa):
    """ normalize and truncate feature map """
    size_x = mapp['size_x']
    size_y = mapp['size_y']
    
    op = SECTOR
    xp = SECTOR * 3
    pp = SECTOR * 12

    idx = np.arange(0, (size_x * size_y * mapp['feature_count']), mapp['feature_count']).reshape(((size_x * size_y), 1)) + np.arange(op)
    part = np.sum(mapp['feature_map'][idx] ** 2, axis=1)

    size_x, size_y = size_x - 2, size_y - 2

    new = np.zeros((size_y * size_x * pp), np.float32)
    func3(new, part, mapp['feature_map'], size_x, size_y, op, xp, pp)
    new[new > alfa] = alfa

    mapp['feature_count'] = pp
    mapp['size_x'] = size_x
    mapp['size_y'] = size_y
    mapp['feature_map'] = new

    return mapp


def get_PCA_feature_maps(mapp):
	size_x = mapp['size_x']
	size_y = mapp['size_y']

	op = mapp['feature_count']
	pp = SECTOR * 3 + 4
	yp = 4
	xp = SECTOR
	nx = 1.0 / np.sqrt(xp * 2)
	ny = 1.0 / np.sqrt(yp)
	
	new = np.zeros((size_x * size_y * pp), np.float32)
	func4(new, mapp['feature_map'], op, size_x, size_y, pp, yp, xp, nx, ny)

	mapp['feature_count'] = pp
	mapp['feature_map'] = new

	return mapp