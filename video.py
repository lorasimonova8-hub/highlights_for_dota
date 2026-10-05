import cv2
import numpy as np
import pandas as pd
import config


class VideoFeatures:

    def __init__(self, ocr_every=1, yolo_every=0, yolo_model=None):
        self.keywords = config.KEYWORDS
        self.ocr_every = ocr_every
        self.yolo_every = yolo_every     
        self.yolo_model = yolo_model

        self.reader = None
        if config.USE_OCR:
            import easyocr
            self.reader = easyocr.Reader(["en", "ru"], gpu=True)

        self.prev_gray = None
        self.n = 0
        self.rows = []

    def process(self, t, frame):
        gray = cv2.cvtColor(cv2.resize(frame, (640, 360)), cv2.COLOR_BGR2GRAY)

        motion = bchange = 0.0
        if self.prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            motion = float(np.mean(np.abs(flow)))
            bchange = abs(float(np.mean(gray)) - float(np.mean(self.prev_gray)))
        self.prev_gray = gray

        row = {"t": t, "motion": motion,
               "brightness": float(np.mean(gray)),
               "brightness_change": bchange,
               "ocr_keywords": "", "heroes_on_screen": None}

        if self.reader and self.n % self.ocr_every == 0:
            row["ocr_keywords"] = ",".join(self._ocr(frame))

        if self.yolo_model and self.yolo_every and self.n % self.yolo_every == 0:
            r = self.yolo_model(frame, verbose=False)[0]
            row["heroes_on_screen"] = sum(
                1 for c in r.boxes.cls if self.yolo_model.names[int(c)] == "person")

        self.rows.append(row)
        self.n += 1
        return row

    def _ocr(self, frame):
        img = cv2.resize(frame, (960, 540))
        found = []
        for _, text, _ in self.reader.readtext(img):
            tl = text.lower()
            for kw in self.keywords:
                w = kw.split()
                if (all(x in tl for x in w[:2]) if len(w) > 1 else kw in tl):
                    found.append(kw)
                    break
        return found

    def df(self):
        return pd.DataFrame(self.rows)