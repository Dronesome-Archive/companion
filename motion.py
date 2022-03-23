import numpy as np

from utils.tracking import iou_tracker, convert_bbox_to_z, convert_x_to_bbox, associate
from filterpy.kalman import KalmanFilter
from pycoral.adapters import detect


class KalmanBoxTracker(object):
    def __init__(self, bbox, min_hits, count=0, num_classes=1, interval=1):
        self.kf = KalmanFilter(dim_x=7, dim_z=4)
        # state transistion matrix
        self.kf.F = np.array(
            [[1, 0, 0, 0, 1, 0, 0],
             [0, 1, 0, 0, 0, 1, 0],
             [0, 0, 1, 0, 0, 0, 1],
             [0, 0, 0, 1, 0, 0, 0],
             [0, 0, 0, 0, 1, 0, 0],
             [0, 0, 0, 0, 0, 1, 0],
             [0, 0, 0, 0, 0, 0, 1]])
        # measurement function
        self.kf.H = np.array(
            [[1, 0, 0, 0, 0, 0, 0],
             [0, 1, 0, 0, 0, 0, 0],
             [0, 0, 1, 0, 0, 0, 0],
             [0, 0, 0, 1, 0, 0, 0]])

        self.kf.R[2:, 2:] *= 10.    # measurement uncertainty / noise
        self.kf.P[4:, 4:] *= 1000.  # covariance matrix
        self.kf.P *= 10.
        self.kf.Q[-1, -1] *= 0.01   # process uncertainty / noise
        self.kf.Q[4:, 4:] *= 0.01

        self.kf.x[:4] = convert_bbox_to_z(bbox)  # filter state estimate
        self.time_since_update = 0
        self.id = count
        self.history = []
        self.hits = 0
        self.hit_streak = 1
        self.age = 0
        self.vip = False
        self.min_hits = min_hits

        # add for relative max_age of the object
        self.previous_x = self.kf.x
        self.obj_speed = 0.
        self.max_age = 0.
        self.is_detect = 0
        # add for saving labels
        self.num_classes = num_classes  # 20 means number classes in PASCAL VOC
        self.interval = interval
        self.label_memory = np.zeros((self.num_classes,), dtype=np.uint16)
        self.label_memory[int(bbox[4])] += 1
        self.labelID = np.argmax(self.label_memory)

    def update(self, bbox):
        # bbox: [x1, y1, x2, y2, label_id]
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        self.kf.update(convert_bbox_to_z(bbox))
        self.previous_x = self.kf.x
        self.is_detect = 1
        self.max_age = self.calculate_max_age()
        self.label_memory[int(bbox[4])] += 1
        self.label_id = np.argmax(self.label_memory)

        if self.hit_streak >= self.min_hits:
            self.vip = True

    def predict(self, active=True):
        #
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] *= 0.0
        self.previous_x = self.kf.x
        self.kf.predict()
        self.age += 1

        if self.time_since_update > 0:
            self.hit_streak = 0

        if active:
            self.time_since_update += 1
        self.history.append(convert_x_to_bbox(self.kf.x))
        self.is_detect = 0

        return self.history[-1]

    def get_state(self):
        return convert_x_to_bbox(self.kf.x)

    def calculate_max_age(self):
        # x, y, w, h, dx, dy, ratio(w/h)
        obj_speed = np.sqrt(self.kf.x[4] ** 2 + self.kf.x[5] ** 2)

        if obj_speed < 1:
            skip_frame = np.minimum(20, 10 / (obj_speed + 1e-7))
        elif obj_speed < 10:
            skip_frame = np.maximum(3, 15 / (obj_speed + 1e-7))
        else: # >= 10
            skip_frame = 10

        return int(skip_frame / self.interval)


class Tracker(object):
    def __init__(self, shape, min_hits=0, num_classes=1, interval=1):
        self.img_shape = shape
        self.min_hits = min_hits
        self.num_classes = num_classes
        self.interval = interval
        self.trackers = []
        self.frame_count = 0
        self.kalman_count = 0
        self.skip_ratio = 0.04

    def update(self, obj_detections, obj_labels, active=True):
        self.frame_count += 1

        # delete too small objects
        detections = []
        for idx in range(obj_detections.shape[0]):
            if (obj_detections[idx][2] - obj_detections[idx][0] >= self.skip_ratio * self.img_shape[0]) and (
                    obj_detections[idx][3] - obj_detections[idx][1] >= self.skip_ratio * self.img_shape[1]):
                detections.append(np.hstack((obj_detections[idx], obj_labels[idx])))
        detections = np.asarray(detections)

        trks = np.zeros((len(self.trackers), 5))
        tdel = []
        ret0 = []
        for t, trk in enumerate(trks):  # t: index, trk: content
            pos = self.trackers[t].predict(active=active)[0]
            trk[:] = [pos[0], pos[1], pos[2], pos[3], 0]
            if np.any(np.isnan(pos)):  # np.isnan: test element-wise for NaN and return result as a bollean array
                tdel.append(t)

        # np.ma.masked_invalid: Mask an array where invalid values occur (NaNs or infs)
        # np.ma.compress_rows: Suppresss whole rows of a 2-D array that contain masked values
        trks = np.ma.compress_rows(np.ma.masked_invalid(trks))
        for t in reversed(tdel):
            self.trackers.pop(t)

        # Hungarian data association
        matched, unmateched_detections, unmatched_trks = associate(detections, trks)

        for t, trk in enumerate(self.trackers):
            if t not in unmatched_trks:
                # np.where returns two array, one is row index, another is column.
                # [[]]->[] dimension changed from (a,b) to (a)
                d = matched[np.where(matched[:, 1] == t)[0], 0]
                trk.update(detections[d, :][0])

        for i in unmateched_detections:
            trk = KalmanBoxTracker(detections[i, :], min_hits=self.min_hits, count=self.kalman_count,
                                   num_classes=self.num_classes, interval=self.interval)
            self.kalman_count += 1
            self.trackers.append(trk)

        i = len(self.trackers)
        for trk in reversed(self.trackers):
            # trk.get_state() is [[]], shape is (1,4), trk.get_state()[0] is [] (shape: (4,))
            # [[1,2]] is a 2d array, shape is (1,2), every row has two elements
            # [1,2] is a one-d array, shape is (2,), this array has two elements
            # [[1],[2]] is a 2d array, shape is (2,1) every row has one elements
            d = trk.get_state()[0]
            # if (trk.time_since_update < trk.max_age) and ((trk.hit_streak >= self.min_hits) or trk.vip):
            if (trk.time_since_update < trk.max_age) and trk.vip:
                ret0.append(np.concatenate((d, [trk.id + 1], [trk.is_detect], [trk.labelID])).reshape(1, -1))

            i -= 1

            if trk.time_since_update > trk.max_age:
                self.trackers.pop(i)

        if len(ret0) > 0:
            # return np.concatenate(ret1)
            return self.hide_boxes(np.concatenate(ret0), active=active)
        else:
            return np.empty((0, 7))

    @staticmethod
    def hide_boxes(detections, active=True):
        # dets: [x1, y1, x2, y2, objID, is_update(0,1), labelID]
        # delete some boxes that included in the big box
        detections[detections < 0.] = 0.  # some kalman predictions results are negative
        detections = detections.astype(np.uint16)

        # x1, y1, x2, y2, id, is_dect:[0, 1]
        num_objects = detections.shape[0]
        flags = np.ones(num_objects, dtype=np.uint8)

        new_detections = []
        for idx_a in range(num_objects):
            for idx_b in range(idx_a+1, num_objects):
                if flags[idx_b] == 0:
                    continue

                if active:
                    # If A include B, and B is predicted then delete B
                    if (detections[idx_a, 0] <= detections[idx_b, 0]) and (detections[idx_a, 1] <= detections[idx_b, 1]) and (
                        detections[idx_a, 2] >= detections[idx_b, 2]) and (detections[idx_a, 3] >= detections[idx_b, 3]) and (
                            detections[idx_b, 5] == 0):
                            flags[idx_b] = 0
                            continue
                    # B inlcude A, and A is predicted tehn delete A
                    elif (detections[idx_a, 0] >= detections[idx_b, 0]) and (detections[idx_a, 1] >= detections[idx_b, 1]) and (
                        detections[idx_a, 2] <= detections[idx_b, 2]) and (detections[idx_a, 3] <= detections[idx_b, 3]) and (
                            detections[idx_a, 5] == 0):
                            flags[idx_a] = 0
                            break

                iou = iou_tracker(detections[idx_a], detections[idx_b])
                if iou >= 0.3:
                    if detections[idx_a, 5] == 0: # (false, false) and (false, true)
                        flags[idx_a] = 0
                        break
                    else:
                        if detections[idx_b, 5] == 0: # (true, false)
                            flags[idx_b] = 0
                            continue
                        else: # (true, true)
                            flags[idx_a] = 0
                            break

        for idx in range(num_objects):
            if flags[idx] == 1:
                new_detections.append(detections[idx])

        return np.asarray(new_detections)