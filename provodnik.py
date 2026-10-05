import os
import json
import numpy as np
import pandas as pd
import config

FEATURES = [
    "duration", "n_channels",
    "has_game", "has_ocr", "has_motion", "has_audio", "has_vision",
    "ocr_weight",
    "max_motion", "max_volume", "max_flash",
    "match_progress",
]


def _seg_max(df, col, s, e):
    if df is None or df.empty or col not in df.columns:
        return 0.0
    v = df.loc[(df["t"] >= s) & (df["t"] <= e), col].max()
    return float(v) if pd.notna(v) else 0.0


def enrich_moments(moments, vdf, adf):
    total = float(vdf["t"].max()) if not vdf.empty else 1.0
    cols = {f: [] for f in FEATURES}

    for _, r in moments.iterrows():
        s, e = r["start"], r["end"]
        chans = str(r["sources"]).split("+") if str(r["sources"]) else []

        cols["duration"].append(e - s)
        cols["n_channels"].append(len(chans))
        cols["has_game"].append(1 if "game" in chans else 0)
        cols["has_ocr"].append(1 if "ocr" in chans else 0)
        cols["has_motion"].append(1 if "motion" in chans else 0)
        cols["has_audio"].append(1 if "audio" in chans else 0)
        cols["has_vision"].append(1 if "vision" in chans else 0)

        et = r["event_type"]
        if et in config.EVENT_SCORES:
            cols["ocr_weight"].append(config.EVENT_SCORES[et])
        elif et == "possible_fight":
            cols["ocr_weight"].append(0)
        else:
            cols["ocr_weight"].append(config.DEFAULT_OCR_SCORE)

        cols["max_motion"].append(_seg_max(vdf, "motion", s, e))
        cols["max_flash"].append(_seg_max(vdf, "brightness_change", s, e))
        cols["max_volume"].append(_seg_max(adf, "volume", s, e))
        cols["match_progress"].append(min(s / total, 1.0)) 

    for f, vals in cols.items():
        moments[f] = vals
    return moments


def save_features(moments, video_file, match_id=None):
    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_file TEXT, match_id INTEGER, start REAL, end REAL, X TEXT)""")
    for _, r in moments.iterrows():
        x = {f: float(r[f]) for f in FEATURES}
        conn.execute("INSERT INTO features (video_file, match_id, start, end, X) VALUES (?,?,?,?,?)",
                     (video_file, match_id, round(r["start"], 2), round(r["end"], 2), json.dumps(x)))
    conn.commit()
    conn.close()


def apply_model_confidence(moments, model_path="model.pkl"):
    if not os.path.exists(model_path) or moments.empty:
        return moments
    import joblib
    model = joblib.load(model_path)
    moments["confidence"] = model.predict_proba(moments[FEATURES])[:, 1].round(2)
    return moments