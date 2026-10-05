import time
import os
import numpy as np   
import cv2

def find_video_file(folder):
    for name in os.listdir(folder):
        if name.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".webm")):
            return os.path.join(folder, name)
    return None


class FileVideoSource:

    def __init__(self, path, step_sec=1.0):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise IOError(f"Не открылось видео: {path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.step = max(int(self.fps * step_sec), 1)

    def frames(self):
        n = 0
        while True:
            if not self.cap.grab():
                break
            if n % self.step == 0:
                ok, frame = self.cap.retrieve()
                if not ok:
                    break
                yield n / self.fps, frame
            n += 1
        self.cap.release()


def file_audio_chunks(path, chunk_sec=0.5, sr=16000):
    import librosa
    y, _ = librosa.load(path, sr=sr)
    hop = int(sr * chunk_sec)
    for i in range(0, len(y) - hop, hop):
        yield i / sr, y[i:i + hop]


#  LIVE

class ScreenVideoSource:
    def __init__(self, monitor_index=1, step_sec=1.0):
        import mss
        self._mss, self._idx, self._step = mss, monitor_index, step_sec

    def frames(self):
        with self._mss.mss() as sct:
            mon = sct.monitors[self._idx]
            t0 = time.time()
            while True:
                img = np.asarray(sct.grab(mon))
                yield time.time() - t0, cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                time.sleep(self._step)


def live_audio_chunks(chunk_sec=0.5, sr=16000):
    import soundcard as sc
    spk = sc.default_speaker()
    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
    frames = int(sr * chunk_sec)
    with mic.recorder(samplerate=sr) as rec:
        t0 = time.time()
        while True:
            data = rec.record(numframes=frames)
            yield time.time() - t0, data.mean(axis=1)