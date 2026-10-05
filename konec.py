import pandas as pd
import config
from sources import FileVideoSource, file_audio_chunks, find_video_file
from video import VideoFeatures
from audio import AudioFeatures, whisper_words, extract_audio_from_video
from score import extract_signals, build_moments, save_db
from provodnik import enrich_moments, save_features, apply_model_confidence


def to_seconds(s):
    p = list(map(int, s.split(":")))
    return p[-1] + p[-2] * 60 + (p[-3] * 3600 if len(p) == 3 else 0)


def main():
    video_path = config.VIDEO_PATH or find_video_file(config.VIDEO_FOLDER)
    if not video_path:
        print(f"В папке {config.VIDEO_FOLDER} нет видео!")
        return
    print(f"Видео: {video_path}")

    horn = to_seconds(config.KNOWN_VIDEO_TIMESTAMP)
    print(f"Горн: {horn} сек\n")


    print("=== ВИДЕО ===")
    yolo_model = None
    if config.USE_YOLO:
        from ultralytics import YOLO  
        yolo_model = YOLO("yolov8n.pt")

    vf = VideoFeatures(ocr_every=config.OCR_EVERY,
                       yolo_every=config.YOLO_EVERY, yolo_model=yolo_model)
    for t, frame in FileVideoSource(video_path, config.VIDEO_STEP_SEC).frames():
        vf.process(t, frame)
        print(f"\r  {t:7.0f} сек", end="")

    vdf = vf.df()
    horn30 = horn - 30
    vdf = vdf[vdf["t"] >= horn30].reset_index(drop=True)
    vdf.to_csv("video_features.csv", index=False)
    print(f"\n  строк: {len(vdf)} (прегейм отсечён: анализ с {horn30:.0f}s)\n")

    print("=== АУДИО ===")
    audio_path = config.AUDIO_PATH
    if not audio_path:
        print("  AUDIO_PATH пуст - извлекается звук из видео ")
        audio_path = extract_audio_from_video(video_path)
        print(f"  звук: {audio_path}")

    af = AudioFeatures()
    for t, chunk in file_audio_chunks(audio_path, config.AUDIO_CHUNK_SEC):
        af.process(t, chunk)

    adf = af.df()
    adf = adf[adf["t"] >= horn30].reset_index(drop=True)
    adf.to_csv("audio_features.csv", index=False)
    print(f"  строк: {len(adf)} (прегейм отсечён)\n")

    rate_df = None
    if config.USE_WHISPER:
        print("=== WHISPER ===")
        _, rate_df = whisper_words(audio_path)
        rate_df.to_csv("speech_rate.csv", index=False)
        print(f"  точек темпа: {len(rate_df)}\n")

    
    game_sig = pd.DataFrame(columns=["t", "channel", "keyword"])
    if config.USE_GAME:
        print("=== ИГРОВЫЕ ФАКТЫ ===")
        from game_local import fetch_parser_signals
        game_sig = fetch_parser_signals()
        print()

    
    print("=== СКЛЕЙКА ===")
    signals = extract_signals(vdf, adf, rate_df)
    if not game_sig.empty:
        signals = pd.concat([signals, game_sig], ignore_index=True)
    moments = build_moments(signals)
    moments = enrich_moments(moments, vdf, adf)
    moments = apply_model_confidence(moments)

    if moments.empty:
        print("Моментов выше порога не найдено. Проверить горн и пороги в config.py")
        return

    moments.to_csv("moments_fused.csv", index=False)
    save_db(moments, video_file=video_path)
    save_features(moments, video_path, config.MATCH_ID)
    print(moments[["event_type", "sources", "score", "confidence",
                   "start", "end"]].to_string())
    print(f"\nГотово: {len(moments)} моментов -> highlights.db, moments_fused.csv")
    print("Дальше идем shorts.py")


if __name__ == "__main__":
    main()