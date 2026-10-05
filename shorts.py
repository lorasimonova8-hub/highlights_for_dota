import os
import re
import sqlite3
import subprocess
import config
from sources import find_video_file

DB = config.DB_PATH
CLIPS_DIR = "clips"

video_path = config.VIDEO_PATH or find_video_file(config.VIDEO_FOLDER)
if not video_path:
    print("Видео не найдено")
    raise SystemExit

os.makedirs(CLIPS_DIR, exist_ok=True)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT * FROM highlights WHERE verdict='pending' ORDER BY score DESC").fetchall()
print(f"К проверке: {len(rows)} моментов. Видео: {video_path}\n")

for r in rows:
    safe_type = re.sub(r"[^\w\-]", "_", str(r["event_type"]))
    out = os.path.join(
        CLIPS_DIR,
        f"clip_{r['id']}_{int(r['clip_start'])}-{int(r['clip_end'])}_{safe_type}_s{r['score']}.mp4")

    if not os.path.exists(out):
        start = max(r["clip_start"], 0)
        dur = r["clip_end"] - start
        print(f"#{r['id']} [{r['event_type']}] score={r['score']} "
              f"{r['start']:.0f}-{r['end']:.0f}с - нарезается {dur:.0f} сек...")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", f"{start:.1f}", "-i", video_path,
                 "-t", f"{dur:.1f}", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "23", "-c:a", "aac", out],
                check=True, capture_output=True, timeout=300)
        except subprocess.TimeoutExpired:
            print("  ffmpeg завис")
            continue
        except Exception as e:
            print(f"  ffmpeg ошибка: {e} ")
            continue
    else:
        print(f"#{r['id']} [{r['event_type']}] score={r['score']} "
              f"{r['start']:.0f}-{r['end']:.0f}с ({r['sources']}) - {r['description']}")

    try:
        os.startfile(out)
    except AttributeError:
        subprocess.run(["xdg-open", out])

    v = input("  a=хайлат / r=мусор / m=середина / s=позже: ").strip().lower()
    if v == "a":
        conn.execute("UPDATE highlights SET verdict='approved' WHERE id=?", (r["id"],))
        conn.commit()
        print("  -> approved\n")
    elif v == "r":
        conn.execute("UPDATE highlights SET verdict='rejected' WHERE id=?", (r["id"],))
        conn.commit()
        try:
            os.remove(out)
            print("  -> rejected, клип удалён\n")
        except OSError:
            print("  -> rejected\n")
    elif v == "m":
        v2 = input("    m=середина ").strip().lower()
        if v2 == "x":
            conn.execute("UPDATE highlights SET verdict='skipped' WHERE id=?", (r["id"],))
            conn.commit()
            try:
                os.remove(out)
            except OSError:
                pass
            print("  -> вне зачёта\n")
        else:
            conn.execute("UPDATE highlights SET verdict='mid' WHERE id=?", (r["id"],))
            conn.commit()
            try:
                os.remove(out)
            except OSError:
                pass
            print("  -> середина (mid) записана\n")
    elif v == "d":
        conn.execute("UPDATE highlights SET verdict='skipped' WHERE id=?", (r["id"],))
        conn.commit()
        try:
            os.remove(out)
        except OSError:
            pass
        print("  -> в корзину\n")
    else:
        print("  -> отложено\n")

conn.close()
print("Готово. Вердикты в БД ")