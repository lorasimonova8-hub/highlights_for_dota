import pandas as pd
import config
from score import extract_signals, build_moments, save_db
from provodnik import enrich_moments, save_features, apply_model_confidence
from sources import find_video_file
from game_local import fetch_parser_signals

video_path = config.VIDEO_PATH or find_video_file(config.VIDEO_FOLDER)
vdf = pd.read_csv("video_features.csv")
adf = pd.read_csv("audio_features.csv")

game_sig = fetch_parser_signals(None)
print(f"фактов из парсера: {len(game_sig)}")
if game_sig.empty:
    print("!!! фактов НЕТ проверить events.json в PARSER_DIR")
else:
    print(game_sig.head(5).to_string())

signals = extract_signals(vdf, adf)
signals = pd.concat([signals, game_sig], ignore_index=True)
print("каналы в сигналах:", signals["channel"].unique().tolist())

moments = build_moments(signals)
moments = enrich_moments(moments, vdf, adf)
moments = apply_model_confidence(moments)
moments.to_csv("moments_fused.csv", index=False)
save_db(moments, video_file=video_path)
save_features(moments, video_path, config.MATCH_ID)
print(f"Готово: {len(moments)} моментов")
print(moments[["event_type","sources","score","start","end"]].to_string())