# camera.py
import cv2
import time
from detection import ObjectDetector

# Stream çalışan tarafta güncellenen global sayaçlar
latest_counts = {
    "person": 0,
    "vehicle": 0,
    "last_update": 0.0,
}


class VideoCamera:
    def __init__(self, source=0):
        """
        source:
          - int -> webcam index (0)
          - str -> video dosya yolu
        """
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Video kaynağı açılamadı: {source}")

        self.detector = ObjectDetector()

        # Kullanıcı ayarları:
        self.detect_people = True
        self.detect_vehicles = False

        # Anlık istatistikler:
        self.person_count = 0
        self.vehicle_count = 0
        self.last_update = 0.0

    def __del__(self):
        if hasattr(self, "cap") and self.cap is not None and self.cap.isOpened():
            self.cap.release()

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            # Video dosyası bitti ise başa sar
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                return None

        boxes, counts = self.detector.detect(
            frame,
            detect_people=self.detect_people,
            detect_vehicles=self.detect_vehicles,
        )

        frame_out = self.detector.draw_boxes(frame, boxes)

        self.person_count = counts.get("person", 0)
        self.vehicle_count = counts.get("vehicle", 0)
        self.last_update = time.time()

        # Global sayaçları da güncelle
        latest_counts["person"] = self.person_count
        latest_counts["vehicle"] = self.vehicle_count
        latest_counts["last_update"] = self.last_update

        return frame_out


def mjpeg_generator(camera: VideoCamera):
    while True:
        frame_bgr = camera.get_frame()
        if frame_bgr is None:
            break

        ret, jpeg = cv2.imencode(".jpg", frame_bgr)
        if not ret:
            continue
        data = jpeg.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
        )
