import numpy as np
import os

from cv2 import cv2


MAX_BOXES = 5

def sigmoid(x):
    return 1. / (1 + np.exp(-x))


def reshape(image, shape):
    iw, ih = image.shape[0: 2][:: -1]
    tw, th = shape

    scale = min(tw / iw, th / ih)
    nw = int(iw * scale)
    nh = int(ih * scale)

    image = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_CUBIC)
    out = np.zeros((shape[1], shape[0], 3), np.uint8)
    out.fill(128)

    dx = (tw - nw) // 2
    dy = (th - nh) // 2
    out[dy: dy + nh, dx: dx + nw, :] = image
    
    return out


def features_to_boxes(outputs, anchors, classes, input_shape, original_shape, threshold):
    grid_shape = outputs.shape[1: 3]
    
    n_anchors = len(anchors)
    n_classes = len(classes)

    # Numpy screwaround to get the boxes in reasonable amount of time
    grid_y = np.tile(np.arange(grid_shape[0]).reshape(-1, 1), grid_shape[0]).reshape(1, grid_shape[0], grid_shape[0], 1).astype(np.float32)
    grid_x = grid_y.copy().T.reshape(1, grid_shape[0], grid_shape[1], 1).astype(np.float32)
    
    outputs = outputs.reshape(1, grid_shape[0], grid_shape[1], n_anchors, -1)
    
    _anchors = anchors.reshape(1, 1, 3, 2).astype(np.float32)

    # Get box parameters from network output and apply transformations
    bx = (sigmoid(outputs[..., 0]) + grid_x) / grid_shape[0] 
    by = (sigmoid(outputs[..., 1]) + grid_y) / grid_shape[1]
    # Should these be inverted? plws update docs!!!
    bw = np.multiply(_anchors[..., 0] / input_shape[1], np.exp(outputs[..., 2]))
    bh = np.multiply(_anchors[..., 1] / input_shape[2], np.exp(outputs[..., 3]))

    # Get the scores 
    scores = sigmoid(np.expand_dims(outputs[..., 4], -1)) * sigmoid(outputs[..., 5:])
    scores = scores.reshape(-1, n_classes)

    # Reshape boxes and scale back to original image size
    ratio = input_shape[2] / original_shape[1]
    letterboxed_height = ratio * original_shape[0] 
    scale = input_shape[1] / letterboxed_height
    offset = (input_shape[1] - letterboxed_height) / 2 / input_shape[1]
    bx = bx.flatten()
    by = (by.flatten() - offset) * scale
    bw = bw.flatten()
    bh = bh.flatten() * scale
    half_bw = bw / 2.
    half_bh = bh / 2.

    tl_x = np.multiply(bx - half_bw, original_shape[1])
    tl_y = np.multiply(by - half_bh, original_shape[0]) 
    br_x = np.multiply(bx + half_bw, original_shape[1])
    br_y = np.multiply(by + half_bh, original_shape[0])

    # Get indices of boxes with score higher than threshold
    indices = np.argwhere(scores >= threshold)
    selected_boxes = []
    selected_scores = []
    for i in indices:
        i = tuple(i)
        selected_boxes.append( ((tl_x[i[0]], tl_y[i[0]]), (br_x[i[0]], br_y[i[0]])) )
        selected_scores.append(scores[i])

    selected_boxes = np.array(selected_boxes)
    selected_scores = np.array(selected_scores)
    selected_classes = indices[:, 1]

    return selected_boxes, selected_scores, selected_classes


def get_anchors(path):
    anchors_path = os.path.expanduser(path)
    with open(anchors_path, mode='r') as f:
        anchors = f.readline()
    anchors = [float(x) for x in anchors.split(',')]
    
    return np.array(anchors).reshape(-1, 2)


def get_classes(path):
    classes_path = os.path.expanduser(path)
    with open(classes_path, mode='r') as f:
        classes = [line.strip('\n') for line in f.readlines()]
    
    return classes