import sqlite3
c = sqlite3.connect("highlights.db")

stat = input("какие хочешь? (r=rejected / d=skipped / s=pending / все=Enter): ").strip().lower()
where = {"r": "verdict='rejected'", "d": "verdict='skipped'", "s": "verdict='pending'"}.get(stat, "verdict != 'x'")
rows = list(c.execute(f"""select id, verdict, event_type, round(start), round(end)
                          from highlights where {where} order by id"""))
if not rows:
    print("пусто")
for r in rows:
    print(f"id={r[0]:3d}  [{r[1]:9s}]  {r[3]:6.0f}-{r[4]:6.0f}  {r[2]}")

mid = int(input("\nid момента: "))
if mid:
    cur = c.execute("select verdict from highlights where id=?", (mid,)).fetchone()
    if cur is None:
        print("такого id нет")
    else:
        print(f"сейчас: {cur[0]}")
        new = input("новый вердикт (a=approved / r=rejected / m=mid / d=skipped / p=pending): ").strip().lower()
        mp = {"a": "approved", "r": "rejected", "m": "mid", "d": "skipped", "p": "pending"}
        if new in mp:
            c.execute("update highlights set verdict=? where id=?", (mp[new], mid))
            c.commit()
            print(f"готово: #{mid} теперь {mp[new]}")
c.close()