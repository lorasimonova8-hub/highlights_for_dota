import numpy as np
import pandas as pd


class AudioFeatures:

    def __init__(self):
        self.rows = []

    def process(self, t, chunk):
        row = {"t": t, "volume": float(np.sqrt(np.mean(chunk ** 2)))}
        self.rows.append(row)
        return row

    def df(self):
        return pd.DataFrame(self.rows)


def extract_audio_from_video(video_path, out_wav="audio_from_video.wav", sr=16000):
    import os, subprocess
    if os.path.exists(out_wav):
        return out_wav
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn",
                    "-ac", "1", "-ar", str(sr), out_wav],
                   check=True, capture_output=True)
    return out_wav


def whisper_words(audio_path, model_name="small", language="ru"):
    import whisper
    model = whisper.load_model(model_name)
    res = model.transcribe(audio_path, language=language)
    words = [{"word": w["word"].strip(), "t": w["start"]}
             for seg in res["segments"] if "words" in seg for w in seg["words"]]
    wdf = pd.DataFrame(words, columns=["word", "t"])
    if wdf.empty:
        return wdf, pd.DataFrame(columns=["t", "words_per_sec"])

    times = np.arange(0, wdf["t"].max(), 1.0)
    rate = [((wdf["t"] >= t - 5) & (wdf["t"] < t)).sum() / 5 for t in times]
    return wdf, pd.DataFrame({"t": times, "words_per_sec": rate})