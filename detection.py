# detection.py
import cv2
import numpy as np
import os


class PeopleDetector:
    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect_people(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        scale = 1.0
        max_width = 800
        if w > max_width:
            scale = max_width / w
            frame_resized = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)))
        else:
            frame_resized = frame_bgr

        rects, _ = self.hog.detectMultiScale(
            frame_resized,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )

        boxes = []
        for (x, y, w_box, h_box) in rects:
            x0 = int(x / scale)
            y0 = int(y / scale)
            w0 = int(w_box / scale)
            h0 = int(h_box / scale)
            boxes.append((x0, y0, w0, h0))

        return boxes, len(boxes)


class CarDetectorYOLO:
    """
    YOLO tabanlı araç tespiti (car, bus, truck, motorbike).
    models/ klasörüne aşağıdaki dosyaları koyduğunu varsayıyor:
      - yolov3-tiny.cfg
      - yolov3-tiny.weights
      - coco.names
    Eğer yüklenemezse, sessizce devre dışı kalır.
    """
    def __init__(self):
        self.net = None
        self.output_layers = []
        self.classes = []
        self.vehicle_classes = {"car", "bus", "truck", "motorbike"}

        base = os.path.join(os.path.dirname(__file__), "models")
        cfg_path = os.path.join(base, "yolov3-tiny.cfg")
        weights_path = os.path.join(base, "yolov3-tiny.weights")
        names_path = os.path.join(base, "coco.names")

        if os.path.exists(cfg_path) and os.path.exists(weights_path) and os.path.exists(names_path):
            try:
                self.net = cv2.dnn.readNetFromDarknet(cfg_path, weights_path)
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

                with open(names_path, "r", encoding="utf-8") as f:
                    self.classes = [line.strip() for line in f.readlines()]

                layer_names = self.net.getLayerNames()
                self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers().flatten()]
            except Exception:
                self.net = None  # YOLO kullanılamaz
        else:
            self.net = None

    def detect_vehicles(self, frame_bgr):
        if self.net is None:
            # YOLO yoksa tespit yapma
            return [], 0

        height, width = frame_bgr.shape[:2]

        blob = cv2.dnn.blobFromImage(
            frame_bgr, 1 / 255.0, (416, 416),
            swapRB=True, crop=False
        )
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

        boxes = []
        confidences = []
        class_ids = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                if confidence > 0.5:
                    class_name = self.classes[class_id] if class_id < len(self.classes) else ""
                    if class_name in self.vehicle_classes:
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)

                        boxes.append([x, y, w, h])
                        confidences.append(confidence)
                        class_ids.append(class_id)

        idxs = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        final_boxes = []
        if len(idxs) > 0:
            for i in idxs.flatten():
                x, y, w, h = boxes[i]
                final_boxes.append((x, y, w, h))

        return final_boxes, len(final_boxes)


class ObjectDetector:
    def __init__(self):
        self.people_detector = PeopleDetector()
        self.car_detector = CarDetectorYOLO()

    def detect(self, frame_bgr, detect_people=True, detect_vehicles=False):
        """
        Dönüş:
          - boxes: [(x,y,w,h,label), ...]
          - counts: {"person": int, "vehicle": int}
        """
        boxes_all = []
        person_count = 0
        vehicle_count = 0

        if detect_people:
            p_boxes, p_cnt = self.people_detector.detect_people(frame_bgr)
            for (x, y, w, h) in p_boxes:
                boxes_all.append((x, y, w, h, "person"))
            person_count = p_cnt

        if detect_vehicles:
            v_boxes, v_cnt = self.car_detector.detect_vehicles(frame_bgr)
            for (x, y, w, h) in v_boxes:
                boxes_all.append((x, y, w, h, "vehicle"))
            vehicle_count = v_cnt

        return boxes_all, {"person": person_count, "vehicle": vehicle_count}

    def draw_boxes(self, frame_bgr, boxes):
        for (x, y, w, h, label) in boxes:
            if label == "person":
                color = (0, 255, 0)
            else:
                color = (0, 0, 255)

            cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                frame_bgr,
                label,
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA,
            )
        return frame_bgr
