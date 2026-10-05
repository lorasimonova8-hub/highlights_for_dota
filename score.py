import sqlite3
import time
import pandas as pd
import config

BASE_EVENT_SCORES = config.EVENT_SCORES

PRIORITY = ["rampage", "godlike", "aegis", "победа", "victory", "match_end",
            "roshan", "teamfight", "barracks", "unstoppable", "triple kill",
            "тройное убийство", "double kill", "двойное убийство", "buyback",
            "killing spree", "серия убийств", "проливает первую кровь"]


def extract_signals(video_df, audio_df, rate_df=None):
    sig = []
    if "ocr_keywords" in video_df.columns:
        for _, r in video_df[video_df["ocr_keywords"].fillna("") != ""].iterrows():
            for kw in str(r["ocr_keywords"]).split(","):
                kw = kw.strip()
                if kw:
                    sig.append({"t": r["t"], "channel": "ocr", "keyword": kw})

    m_thr = video_df["motion"].quantile(config.MOTION_Q)
    for _, r in video_df[video_df["motion"] > m_thr].iterrows():
        sig.append({"t": r["t"], "channel": "motion", "keyword": None})

    if "heroes_on_screen" in video_df.columns:
        for _, r in video_df[video_df["heroes_on_screen"].fillna(0) >= 6].iterrows():
            sig.append({"t": r["t"], "channel": "vision", "keyword": None})

    v_thr = audio_df["volume"].quantile(config.VOLUME_Q)
    for _, r in audio_df[audio_df["volume"] > v_thr].iterrows():
        sig.append({"t": r["t"], "channel": "audio", "keyword": None})

    if rate_df is not None and not rate_df.empty and "words_per_sec" in rate_df:
        r_thr = rate_df["words_per_sec"].quantile(config.RATE_Q)
        for _, r in rate_df[rate_df["words_per_sec"] > r_thr].iterrows():
            sig.append({"t": r["t"], "channel": "audio", "keyword": None})

    return pd.DataFrame(sig, columns=["t", "channel", "keyword"])


def build_moments(signals):
    if signals.empty:
        return pd.DataFrame()

    evs = []
    for ch, g in signals.sort_values("t").groupby("channel"):
        cur = None
        for _, r in g.iterrows():
            if cur and r["t"] - cur["end"] <= config.MERGE_GAP:
                cur["end"] = r["t"]
            else:
                if cur:
                    evs.append(cur)
                cur = {"channel": ch, "keyword": r["keyword"], "start": r["t"], "end": r["t"]}
        if cur:
            evs.append(cur)
    evs = pd.DataFrame(evs)

    # 2) OCR
    evs.loc[evs["channel"] == "ocr", "start"] -= config.OCR_BACKSHIFT

    # 3) склейка
    evs = evs.sort_values("start").reset_index(drop=True)
    merged, cur = [], None
    for _, r in evs.iterrows():
        if cur and r["start"] - cur["end"] <= config.MERGE_GAP:
            cur["end"] = max(cur["end"], r["end"])
            cur["channels"].add(r["channel"])
            if r["keyword"]:
                cur["keywords"].append(r["keyword"])
        else:
            if cur:
                merged.append(cur)
            cur = {"start": r["start"], "end": r["end"],
                   "channels": {r["channel"]},
                   "keywords": [r["keyword"]] if r["keyword"] else []}
    if cur:
        merged.append(cur)
    mom = pd.DataFrame(merged)

    # 4) длинные
    over = (mom["end"] - mom["start"]) > config.MAX_DURATION
    mom.loc[over, "start"] = mom.loc[over, "end"] - config.MAX_DURATION

    # 5) вес калькулятор
    def calculate_score(m):
        ch = m["channels"]
        if "game" in ch or "ocr" in ch:
            base = 0
            for kw in m["keywords"]:
                base = max(base, BASE_EVENT_SCORES.get(kw, 2))

            confirm = len(ch) > 1
            if confirm:
                base += 1

            return min(base, 5)
        if {"motion", "audio", "vision"} <= ch:
            return 3
        return 2
    mom["sources"] = mom["channels"].apply(lambda c: "+".join(sorted(c)))
    mom["score"] = mom.apply(calculate_score, axis=1)

    # 6) начинаем с 5
    def select_main_event(m):
        for p in PRIORITY:
            if p in m["keywords"]:
                return p
        return m["keywords"][0] if m["keywords"] else "unscripted_clash"
    mom["event_type"] = mom.apply(select_main_event, axis=1)

    # 7) время клипов 
    short = (mom["end"] - mom["start"]) < config.MIN_DURATION
    mid = (mom.loc[short, "start"] + mom.loc[short, "end"]) / 2
    mom.loc[short, "start"] = (mid - config.MIN_DURATION / 2).clip(lower=0)
    mom.loc[short, "end"] = mid + config.MIN_DURATION / 2

    # 8) поля выхода
    mom["confidence"] = mom["channels"].apply(
        lambda c: round(min(sum(config.CHANNEL_CONF.get(x, 0.1) for x in c), 0.99), 2))
    mom["description"] = mom.apply(
        lambda r: f"{r['event_type']} ({r['end']-r['start']:.0f}с, score:{r['score']}, {r['sources']})", axis=1)
    mom["recommended_duration"] = ((mom["end"]-mom["start"]).clip(15, 60)
                                   + config.PRE_PAD + config.POST_PAD)

    # 9) порог
    return mom[mom["score"] >= config.SCORE_THRESHOLD].sort_values("start").reset_index(drop=True)

def save_db(moments, video_file):
    conn = sqlite3.connect(config.DB_PATH)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(highlights)")}
    if cols and "start" not in cols:
        conn.execute(f"ALTER TABLE highlights RENAME TO highlights_old_{int(time.time())}")
    conn.execute("""CREATE TABLE IF NOT EXISTS highlights (
        id INTEGER PRIMARY KEY AUTOINCREMENT, video_file TEXT, match_id INTEGER,
        start REAL, end REAL, event_type TEXT, sources TEXT, score INTEGER,
        confidence REAL, description TEXT, recommended_duration REAL,
        clip_start REAL, clip_end REAL,
        status TEXT DEFAULT 'pending', verdict TEXT DEFAULT 'pending')""")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_hl_uniq
                    ON highlights (video_file, start, end, event_type)""")
    for _, r in moments.iterrows():
        conn.execute(
            "INSERT OR IGNORE INTO highlights (video_file, match_id, start, end, event_type,"
            " sources, score, confidence, description, recommended_duration, clip_start, clip_end)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (video_file, config.MATCH_ID, r["start"], r["end"], r["event_type"], r["sources"],
             int(r["score"]), r["confidence"], r["description"], r["recommended_duration"],
             max(0.0, r["start"] - config.PRE_PAD), r["end"] + config.POST_PAD))
    conn.commit()
    conn.close()