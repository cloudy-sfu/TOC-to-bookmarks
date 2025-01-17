import cv2
import numpy as np
import pandas as pd

import infer.predict_cls as predict_cls
import infer.predict_det as predict_det
import infer.predict_rec as predict_rec


def get_rotate_crop_image(img, points):
    """
    img_height, img_width = img.shape[0:2]
    left = int(np.min(points[:, 0]))
    right = int(np.max(points[:, 0]))
    top = int(np.min(points[:, 1]))
    bottom = int(np.max(points[:, 1]))
    img_crop = img[top:bottom, left:right, :].copy()
    points[:, 0] = points[:, 0] - left
    points[:, 1] = points[:, 1] - top
    """
    img_crop_width = int(
        max(
            np.linalg.norm(points[0] - points[1]),
            np.linalg.norm(points[2] - points[3])))
    img_crop_height = int(
        max(
            np.linalg.norm(points[0] - points[3]),
            np.linalg.norm(points[1] - points[2])))
    pts_std = np.float32([[0, 0], [img_crop_width, 0],
                          [img_crop_width, img_crop_height],
                          [0, img_crop_height]])
    m = cv2.getPerspectiveTransform(points, pts_std)
    dst_img = cv2.warpPerspective(
        img,
        m, (img_crop_width, img_crop_height),
        borderMode=cv2.BORDER_REPLICATE,
        flags=cv2.INTER_CUBIC)
    dst_img_height, dst_img_width = dst_img.shape[0:2]
    if dst_img_height * 1.0 / dst_img_width >= 1.5:
        dst_img = np.rot90(dst_img)
    return dst_img


class TextSystem(object):
    def __init__(self, args):
        self.text_detector = predict_det.TextDetector(args)
        self.text_recognizer = predict_rec.TextRecognizer(args)
        self.use_angle_cls = args.use_angle_cls
        self.drop_score = args.drop_score
        if self.use_angle_cls:
            self.text_classifier = predict_cls.TextClassifier(args)

    def __call__(self, img):
        ori_im = img.copy()
        """
        dt_boxes (GPT):
        [x0, y0],  Top-left corner
        [x1, y1],  Top-right corner
        [x2, y2],  Bottom-right corner
        [x3, y3],  Bottom-left corner
        x: horizontal position
        y: vertical position
        """
        dt_boxes, elapse = self.text_detector(img)
        if dt_boxes is None:
            return pd.DataFrame()
        img_crop_list = []
        dt_boxes = sorted_boxes(dt_boxes)
        for box in dt_boxes:
            img_crop = get_rotate_crop_image(ori_im, box)
            img_crop_list.append(img_crop)
        if self.use_angle_cls:
            img_crop_list, angle_list, elapse = self.text_classifier(
                img_crop_list)
        rec_res, elapse = self.text_recognizer(img_crop_list)
        results = []
        for box, rec_reuslt in zip(dt_boxes, rec_res):
            box = box.astype(int)
            text, score = rec_reuslt
            if score >= self.drop_score:
                results.append({
                    'left_upper_x': box[0][0],
                    'left_upper_y': box[0][1],
                    'right_upper_x': box[1][0],
                    'right_upper_y': box[1][1],
                    'right_lower_x': box[2][0],
                    'right_lower_y': box[2][1],
                    'left_lower_x': box[3][0],
                    'left_lower_y': box[3][1],
                    'text': text,
                    'confidence': score,
                })
        results = pd.DataFrame(results)
        return results


def sorted_boxes(dt_boxes):
    """
    Sort text boxes in order from top to bottom, left to right
    args:
        dt_boxes(array):detected text boxes with shape [4, 2]
    return:
        sorted boxes(array) with shape [4, 2]
    """
    num_boxes = dt_boxes.shape[0]
    _boxes = sorted(dt_boxes, key=lambda x: (x[0][1], x[0][0]))

    for i in range(num_boxes - 1):
        if abs(_boxes[i + 1][0][1] - _boxes[i][0][1]) < 10 and \
                (_boxes[i + 1][0][0] < _boxes[i][0][0]):
            _boxes[i], _boxes[i + 1] = _boxes[i + 1], _boxes[i]
    return _boxes
