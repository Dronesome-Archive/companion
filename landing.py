import logging
import numpy as np
import asyncio
import time
import math
import cv2

from PIL import Image
from PIL import ImageDraw

from pycoral.adapters import common
from pycoral.adapters import detect
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter

from numpy.linalg import norm
from motion import Tracker

from utils.drawing import draw_objects
from utils.vision import unpack_fingerprint, unpack_scene
from utils.helpers import CALIB, arr_to_bbox, calculate_distance, calculate_focal_length


class ASSETS:
    MODEL = './assets/ssdlite_mobiledet_landingpad_edgetpu.tflite'
    LFILE = './assets/labels.txt'


def __setup_stream(channel):
    # TODO: add picam bindings
    return cv2.VideoCapture(channel)


def __load_interpreter():
    interpreter = make_interpreter(ASSETS.MODEL)
    interpreter.allocate_tensors()

    return interpreter


def __estimate_local_position(source_image, bbox, F):
    root_point = (320, 240)
    
    if len(bbox) < 1:
        return (None, None)
    
    source_image, roi, dim0, center_point = unpack_scene(source_image, arr_to_bbox(bbox[0]))

    if roi is not None:
        fingerprint = unpack_fingerprint(roi)
        
        if len(fingerprint) == 4:
            ratio = math.hypot(root_point[0] - center_point[0],
                               root_point[1] - center_point[1]) / dim0
            
            distance_y = calculate_distance(F, CALIB.REAL_WIDTH, dim0)
            distance_x = (root_point[0] - center_point[0])
            distance_x = distance_y * (distance_x / dim0)
            distance_z = (root_point[1] - center_point[1])
            distance_z = distance_y * (distance_z / dim0)

            return (ratio, (distance_x, distance_y, distance_z))
    
    return (None, None)
        

async def __prepare_landing(system, mav, x, z):
    r_earth = 6371000.0     # in meters
    
    current_pos = mav.pos

    new_latitude  = current_pos[0]  + (z / r_earth) * (180 / math.pi);
    new_longitude = current_pos[1] + (x / r_earth) * (180 / math.pi) / math.cos(current_pos[0] * math.pi/180);

    await system.goto_location(new_latitude, new_longitude, 3, 0)


async def __do_landing(system):
    await system.action.land()


async def do_landing(**kwagrs):
    focal_length = calculate_focal_length(CALIB.REAL_DISTANCE, 
                        CALIB.REAL_WIDTH, CALIB.REFERENCE_WIDTH)
    labels = read_label_file(ASSETS.LFILE) if ASSETS.LFILE else {}
    interpreter = __load_interpreter()

    tracker = Tracker(shape=(320, 320, 3), min_hits=0, num_classes=len(labels),
                      interval=3)
    capture = cv2.VideoCapture(0)
    frameid = 0

    while capture.isOpened():
        return_value, frame = capture.read()

        if not return_value:
            break
        
        x = Image.fromarray(frame)
        _, scale = common.set_resized_input(interpreter, x.size, 
                      lambda size: x.resize(size, Image.ANTIALIAS))

        detections0, labels0, active = (None, None, None) 

        if np.mod(frameid, 3) == 0:
            interpreter.invoke()
            outputs = detect.get_objects(interpreter, 0.8, scale)            
            detections0 = (
                np.array(
                    [
                        [
                            outputs[0].bbox[0],
                            outputs[0].bbox[1],
                            outputs[0].bbox[2],
                            outputs[0].bbox[3],
                        ]
                    ]
                )
                if len(outputs) > 0
                else np.array([])
            )                    
            labels0 = np.array(['0']).astype(np.uint8) if len(outputs) > 0 else np.array([])
            active = True
        elif np.mod(frameid, 3) != 0:
            detections0, labels0 = (np.array([]), np.array([]))
            active = False
        
        tracks0 = tracker.update(detections0, labels0, active)    

        x = np.asarray(x)
        ratio, local_position = __estimate_local_position(x, tracks0, focal_length)

        if ratio is not None:
            logging.info("local-position-estimation: SUCCESS")
            logging.info(f"pos := <{local_position[0]}, {local_position[1]}, {local_position[2]}> [METRIC: CM]")
            
            await __prepare_landing(kwagrs["mavsdk_system"], kwagrs["mav"], local_position[0] / 10, local_position[2] / 10)

            if ratio < 0.16:
                logging.info("drone overlaps with landing pad --> landing")

                await __do_landing(kwagrs["mavsdk_system"])
                logging.info("drone landed")
                break
            
        frameid += 1    
    



