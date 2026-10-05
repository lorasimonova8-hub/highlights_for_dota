import json
import sqlite3
import pandas as pd
import config
from provodnik import FEATURES

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold, cross_val_score
import joblib

MIN_TRAIN = 20

VERDICT_Y = {"approved": 1.0, "mid": 0.5, "rejected": 0.0}


def get_features_table():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        ft = pd.read_sql("SELECT video_file, match_id, start, end, X FROM features", conn)
    except Exception:
        ft = None
    conn.close()
    return ft


def load_admin_examples():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        hl = pd.read_sql("""SELECT video_file, start, end, verdict FROM highlights
                            WHERE verdict IN ('approved','rejected','mid')""", conn)
    except Exception:
        return None, None, None
    conn.close()
    ft = get_features_table()
    if hl.empty or ft is None or ft.empty:
        return None, None, None
    hl["start"], hl["end"] = hl["start"].round(2), hl["end"].round(2)
    ft["start"], ft["end"] = ft["start"].round(2), ft["end"].round(2)
    m = hl.merge(ft, on=["video_file", "start", "end"], how="inner")
    if m.empty:
        return None, None, None
    X = pd.DataFrame([json.loads(x) for x in m["X"]])[FEATURES]
    y = m["verdict"].map(VERDICT_Y)
    return X, y, m["video_file"]


def main():
    Xa, ya, ga = load_admin_examples()
    if Xa is None:
        print("Примеров 0")
        return
    X, y, groups = Xa, ya, ga

    n = len(X)
    if n < MIN_TRAIN:
        print(f"Примеров: {n}, минимум {MIN_TRAIN}.")
        return

    print(f"Примеров: {n} | к 'хорошо': {y.sum():.1f} | к 'мусор': {(1-y).sum():.1f}")

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=1000))

    if groups.nunique() >= 2:
        sc = cross_val_score(model, X, y,
                             cv=GroupKFold(n_splits=min(3, groups.nunique())),
                             groups=groups, scoring="f1")
        print(f"Проверка по целым матчам: F1 = {sc.mean():.2f} ± {sc.std():.2f}")
    
    model.fit(X, y)
    print("\n модель выучила (+ к approved, - к rejected):")
    for f, c in sorted(zip(FEATURES, model[-1].coef_[0]), key=lambda t: -abs(t[1])):
        print(f"  {f:18s} {c:+.2f}")

    if groups.nunique() < 2:
        joblib.dump(model, "model_pilot.pkl")
        print("\nмало матчей")
    else:
        joblib.dump(model, "model.pkl")
        print("\nСохранено для обучения.")


if __name__ == "__main__":
    main()