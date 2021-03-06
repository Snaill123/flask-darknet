# -*- coding: utf-8 -*-

import time
import random

import ctypes


HOME_PATH = "/home/raze/"
DN_PATH = "{}Workspace/darknet/{}".format(HOME_PATH, '{}')


def sample(probs):
    s = sum(probs)
    probs = [a/s for a in probs]
    r = random.uniform(0, 1)
    for i in range(len(probs)):
        r = r - probs[i]
        if r <= 0:
            return i
    return len(probs)-1


def c_array(ctype, values):
    arr = (ctype*len(values))()
    arr[:] = values
    return arr


class BOX(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float),
                ("y", ctypes.c_float),
                ("w", ctypes.c_float),
                ("h", ctypes.c_float)]


class DETECTION(ctypes.Structure):
    _fields_ = [("bbox", BOX),
                ("classes", ctypes.c_int),
                ("prob", ctypes.POINTER(ctypes.c_float)),
                ("mask", ctypes.POINTER(ctypes.c_float)),
                ("objectness", ctypes.c_float),
                ("sort_class", ctypes.c_int)]


class IMAGE(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int),
                ("h", ctypes.c_int),
                ("c", ctypes.c_int),
                ("data", ctypes.POINTER(ctypes.c_float))]


class METADATA(ctypes.Structure):
    _fields_ = [("classes", ctypes.c_int),
                ("names", ctypes.POINTER(ctypes.c_char_p))]


lib = ctypes.CDLL(DN_PATH.format("libdarknet.so"), ctypes.RTLD_GLOBAL)
lib.network_width.argtypes = [ctypes.c_void_p]
lib.network_width.restype = ctypes.c_int
lib.network_height.argtypes = [ctypes.c_void_p]
lib.network_height.restype = ctypes.c_int

predict = lib.network_predict
predict.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)]
predict.restype = ctypes.POINTER(ctypes.c_float)

set_gpu = lib.cuda_set_device
set_gpu.argtypes = [ctypes.c_int]

make_image = lib.make_image
make_image.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [ctypes.c_void_p, ctypes.c_int,
                              ctypes.c_int, ctypes.c_float,
                              ctypes.c_float, ctypes.POINTER(ctypes.c_int),
                              ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
get_network_boxes.restype = ctypes.POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [ctypes.c_void_p]
make_network_boxes.restype = ctypes.POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [ctypes.POINTER(DETECTION), ctypes.c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_int]

network_predict = lib.network_predict
network_predict.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [ctypes.c_void_p]

load_net = lib.load_network
load_net.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
load_net.restype = ctypes.c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [ctypes.POINTER(DETECTION), ctypes.c_int, ctypes.c_int, ctypes.c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [ctypes.POINTER(DETECTION), ctypes.c_int, ctypes.c_int, ctypes.c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, ctypes.c_int, ctypes.c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [ctypes.c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [ctypes.c_void_p, IMAGE]
predict_image.restype = ctypes.POINTER(ctypes.c_float)


def classify(net, meta, im):
    out = predict_image(net, im)
    res = []
    for i in range(meta.classes):
        res.append((meta.names[i], out[i]))
    return sorted(res, key=lambda x: -x[1])


def detect(net, meta, image, thresh=.5, hier_thresh=.5, nms=.45):
    im = load_image(image, 0, 0)
    num = ctypes.c_int(0)
    pnum = ctypes.pointer(num)
    predict_image(net, im)
    dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum)
    num = pnum[0]
    if (nms): do_nms_obj(dets, num, meta.classes, nms);

    res = []
    for j in range(num):
        for i in range(meta.classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                res.append((meta.names[i], dets[j].prob[i], (b.x, b.y, b.w, b.h)))
    res = sorted(res, key=lambda x: -x[1])
    free_image(im)
    free_detections(dets, num)
    return res


if __name__ == "__main__":
    beginnings_time = time.time()
    net = load_net(DN_PATH.format("cfg/darknet19.cfg").encode("ascii"),
                   DN_PATH.format("darknet19.weights").encode("ascii"), 0)
    img_path = HOME_PATH + "Descargas/nahui.jpeg"
    im = load_image(img_path.encode("ascii"), 0, 0)
    meta = load_meta(DN_PATH.format("cfg/imagenet1k.data").encode("ascii"))
    r = classify(net, meta, im)
    elapsed_time = time.time() - beginnings_time
    print("Elapsed time: {} seconds".format(elapsed_time))
    print(r[:10])
    # net = load_net(DN_PATH.format("cfg/yolov2-tiny.cfg"), DN_PATH.format("yolov2-tiny.weights"), 0)
    # meta = load_meta(DN_PATH.format("cfg/coco.data"))
    # r = detect(net, meta, DN_PATH.format("data/dog.jpg"))
    # print(r)
    

