import json
import os
import pandas as pd
import config

IMPORTANT_EVENTS = {
    "DOTA_COMBATLOG_MULTIKILL",
    "DOTA_COMBATLOG_KILLSTREAK",
    "DOTA_COMBATLOG_FIRST_BLOOD",
    "DOTA_COMBATLOG_BUYBACK",
    "DOTA_COMBATLOG_TEAM_BUILDING_KILL",
    "DOTA_COMBATLOG_DEATH",
}

MK_NAMES = {2: "double kill", 3: "triple kill", 4: "ultra kill", 5: "rampage"}


def time_to_seconds(s):
    p = list(map(int, str(s).split(":")))
    return p[-1] + p[-2] * 60 + (p[-3] * 3600 if len(p) == 3 else 0)


def calculate_time_offset():
    hor_video = time_to_seconds(config.KNOWN_VIDEO_TIMESTAMP)
    gs = 0.0
    sp = os.path.join(config.PARSER_DIR, "summary.json")
    if os.path.exists(sp):
        try:
            gs = float(json.load(open(sp, encoding="utf-8")).get("game_start_timestamp", 0.0))
        except Exception as e:
            print(f"[WARN] summary: {e}")
    shift = hor_video - gs
    print(f"привязка: горн ролика {hor_video}s, горн реплея {gs:.1f}s -> сдвиг {shift:.1f}")
    return shift


def _mk_name(val):
    try:
        return MK_NAMES.get(int(val))
    except (TypeError, ValueError):
        return None


def _ks_name(val):
    try:
        v = int(val)
    except (TypeError, ValueError):
        return None
    if v >= 9:
        return "godlike"
    if v >= 6:
        return "unstoppable"
    if v >= 3:
        return "killing spree"
    return None


def _score_for(event_type, ev):
    if event_type == "DOTA_COMBATLOG_MULTIKILL":
        kw = _mk_name(ev.get("value"))
        if kw:
            return float(config.EVENT_SCORES.get(kw, 3)), kw
        return 0.0, ""
    if event_type == "DOTA_COMBATLOG_KILLSTREAK":
        kw = _ks_name(ev.get("value"))
        if kw:
            return float(config.EVENT_SCORES.get(kw, 3)), kw
        return 0.0, ""
    if event_type == "DOTA_COMBATLOG_FIRST_BLOOD":
        return float(config.EVENT_SCORES.get("проливает первую кровь", 2)), "проливает первую кровь"
    if event_type == "DOTA_COMBATLOG_BUYBACK":
        return float(config.EVENT_SCORES.get("buyback", 3)), "buyback"
    if event_type == "DOTA_COMBATLOG_TEAM_BUILDING_KILL":
        tgt = str(ev.get("target", "")).lower()
        if "barracks" in tgt:
            return float(config.EVENT_SCORES.get("barracks", 4)), "barracks"
        return 0.0, ""
    if event_type == "DOTA_COMBATLOG_DEATH":
        tgt = str(ev.get("target", "")).lower()
        if tgt == "npc_dota_roshan":
            return float(config.EVENT_SCORES.get("roshan", 4)), "roshan"
        return 0.0, ""
    return 0.0, ""


def parse_game_events(json_path, shift):
    if not os.path.exists(json_path):
        print(f"нет файла: {json_path}")
        return pd.DataFrame()

    sp = os.path.join(config.PARSER_DIR, "summary.json")
    gs = ge = None
    if os.path.exists(sp):
        try:
            s = json.load(open(sp, encoding="utf-8"))
            gs = s.get("game_start_timestamp")
            ge = s.get("game_end_timestamp")
        except Exception as e:
            print(f"[WARN] summary: {e}")

    data = json.load(open(json_path, encoding="utf-8"))
    raw = data if isinstance(data, list) else data.get("events", [])

    rows = []
    death_times = []

    for ev in raw:
        event_type = ev.get("type", "")
        if event_type not in IMPORTANT_EVENTS:
            continue
        tr = ev.get("timestampRaw", ev.get("timestamp"))
        if not isinstance(tr, (int, float)):
            continue
        if gs is not None and tr < gs - 5:
            continue
        if ge is not None and tr > ge + 5:
            continue

        t_video = tr + shift
        score, keyword = _score_for(event_type, ev)

        if event_type == "DOTA_COMBATLOG_DEATH" and ev.get("countedHeroDeath"):
            death_times.append(t_video)

        if score <= 0:
            continue

        rows.append({
            "t": t_video,
            "channel": "game",
            "keyword": keyword,
            "score": score,
            "confidence": config.CHANNEL_CONF.get("game", 0.85),
        })

    death_times.sort()
    i = 0
    tfs = []
    while i < len(death_times):
        j = i
        while j < len(death_times) and death_times[j] - death_times[i] <= 25:
            j += 1
        if j - i >= 4:
            tfs.append({
                "t": death_times[i], "channel": "game", "keyword": "teamfight",
                "score": float(config.EVENT_SCORES.get("teamfight", 4)),
                "confidence": config.CHANNEL_CONF.get("game", 0.85),
            })
            i = j
        else:
            i += 1
    if tfs:
        rows.extend(tfs)

    return pd.DataFrame(rows)


def fetch_parser_signals(horn_offset=None):
    json_path = os.path.join(config.PARSER_DIR, "events.json")
    shift = calculate_time_offset()
    df = parse_game_events(json_path, shift)
    if df.empty:
        return pd.DataFrame(columns=["t", "channel", "keyword"])
    return df[["t", "channel", "keyword"]]


if __name__ == "__main__":
    pass