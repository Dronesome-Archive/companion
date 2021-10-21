import numpy as np
import tensorflow as tf

from cv2 import cv2


EDGETPU_SHARED_LIB = 'libedgetpu.so.1'

class Detector(object):
    

    def get_interpreter_details(interpreter):
        inp_details = interpreter.get_input_details()
        out_details = interpreter.get_output_details()
       
        inp_shape = inp_details[0]['shape']

        return inp_details, out_details, inp_shape