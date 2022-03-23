import numpy as np

from scipy.optimize import linear_sum_assignment


def iou_tracker(bb_test_, bb_gt_):
    bb_test = bb_test_.copy().astype(np.float32)
    bb_gt = bb_gt_.copy().astype(np.float32)

    xx1 = np.maximum(bb_test[0], bb_gt[0])  # x1
    yy1 = np.maximum(bb_test[1], bb_gt[1])  # x2
    xx2 = np.minimum(bb_test[2], bb_gt[2])  # x3
    yy2 = np.minimum(bb_test[3], bb_gt[3])  # x4
    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    wh = w * h
    iou = wh / ((bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1]) + (
            bb_gt[2] - bb_gt[0]) * (bb_gt[3] - bb_gt[1]) - wh)
    return iou


def convert_bbox_to_z(bbox):
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = bbox[0] + w / 2
    y = bbox[1] + h / 2
    s = w * h
    r = w / float(h)
    return np.array([x, y, s, r]).reshape((4, 1))  # center_x, center_y, area, ratio


def convert_x_to_bbox(x, score=None):
    w = np.sqrt(x[2] * x[3])
    h = x[2] / w
    if score is None:
        return np.array([
            x[0] - w / 2., x[1] - h / 2., 
            x[0] + w / 2., x[1] + h / 2.
        ]).reshape((1, 4))  # x1, y1, x2, y2
    else:
        return np.array([
            x[0] - w / 2., x[1] - h / 2., 
            x[0] + w / 2., x[1] + h / 2., score
        ]).reshape((1, 5))


def linear_assignment(matrix):
    indices = linear_sum_assignment(matrix)
    if len(matrix) < 1:
        return np.empty((0, 2), dtype=np.int64)
    
    return np.array([
        [
            indices[0][0], 
            indices[1][0]
        ]
    ])


def associate(detections, trackers, iou_threshold=0.3):
    if len(trackers) == 0:
        return np.empty((0, 2), dtype=int), np.arange(len(detections)), np.empty((0, 5), dtype=int)

    iou_matrix = np.zeros((len(detections), len(trackers)), dtype=np.float32)

    for d, det in enumerate(detections):
        for t, trk in enumerate(trackers):
            iou_matrix[d, t] = iou_tracker(trk, det)

    # Solve the linear assignment problem using the Hungarian algorithm
    # The problem is also known as maximum weight matching in bipartite graphs. The method is also known as the
    # Munkres or Kuhn-Munkres algorithm.
    matched_indices = linear_assignment(-iou_matrix)

    unmatched_detections = []
    for d, det in enumerate(detections):
        if d not in matched_indices[:, 0]:
            unmatched_detections.append(d)  # store index

    unmatched_trackers = []
    for t, trk in enumerate(trackers):
        if t not in matched_indices[:, 1]:
            unmatched_trackers.append(t)  # store index

    matches = []
    for m in matched_indices:
        if iou_matrix[m[0], m[1]] < iou_threshold:
            unmatched_detections.append(m[0])
            unmatched_trackers.append(m[1])
        else:
            matches.append(m.reshape(1, 2))

    if len(matches) == 0:
        matches = np.empty((0, 2), dtype=int)
    else:
        matches = np.concatenate(matches, axis=0)

    return matches, np.array(unmatched_detections), np.array(unmatched_trackers)