"""
Train and compare several ML models, then save the best one.

Models compared:
    - Logistic Regression
    - Multinomial Naive Bayes
    - Passive Aggressive Classifier (calibrated for probabilities)
    - Random Forest

Usage:
    python backend/train_model.py                    # uses data/sample_news.csv
    python backend/train_model.py data/news.csv      # use your own dataset
    python backend/train_model.py --with-feedback    # also learn from user feedback in SQLite

CSV must have columns: text, label   (label = REAL or FAKE)
"""
import json
import os
import sys
from datetime import datetime

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, PassiveAggressiveClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from preprocess import clean_text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA = os.path.join(BASE_DIR, "data", "sample_news.csv")
MODEL_DIR = os.path.join(BASE_DIR, "model")
MODEL_PATH = os.path.join(MODEL_DIR, "fake_news_model.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")


def candidate_models():
    return {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Naive Bayes": MultinomialNB(),
        "Passive Aggressive": CalibratedClassifierCV(PassiveAggressiveClassifier(max_iter=1000), cv=3),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42),
    }


def load_feedback_rows():
    """Corrected labels that users submitted through the app."""
    import database
    database.init_db()
    rows = database.get_feedback_for_training()
    return pd.DataFrame(rows, columns=["text", "label"]) if rows else pd.DataFrame(columns=["text", "label"])


def train(data_path=DEFAULT_DATA, with_feedback=False, verbose=True):
    df = pd.read_csv(data_path)
    df = df.dropna(subset=["text", "label"])[["text", "label"]]
    if with_feedback:
        fb = load_feedback_rows()
        if verbose:
            print(f"Adding {len(fb)} feedback rows")
        df = pd.concat([df, fb], ignore_index=True)

    df["label"] = df["label"].astype(str).str.upper().str.strip()
    df["clean"] = df["text"].apply(clean_text)

    X_train, X_test, y_train, y_test = train_test_split(
        df["clean"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    results, best_name, best_pipe, best_f1 = [], None, None, -1
    for name, clf in candidate_models().items():
        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_df=0.9)),
            ("clf", clf),
        ])
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)
        m = {
            "model": name,
            "accuracy": round(accuracy_score(y_test, preds) * 100, 2),
            "precision": round(precision_score(y_test, preds, pos_label="FAKE", zero_division=0) * 100, 2),
            "recall": round(recall_score(y_test, preds, pos_label="FAKE", zero_division=0) * 100, 2),
            "f1": round(f1_score(y_test, preds, pos_label="FAKE", zero_division=0) * 100, 2),
            "confusion_matrix": confusion_matrix(y_test, preds, labels=["REAL", "FAKE"]).tolist(),
        }
        results.append(m)
        if verbose:
            print(f"{name:22s} acc={m['accuracy']:6.2f}%  f1={m['f1']:6.2f}%")
        if m["f1"] > best_f1:
            best_name, best_pipe, best_f1 = name, pipe, m["f1"]

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(best_pipe, MODEL_PATH)
    metrics = {
        "best_model": best_name,
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dataset": os.path.basename(data_path),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "results": results,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    if verbose:
        print(f"\nBest model: {best_name}  -> saved to {MODEL_PATH}")
    return metrics


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    train(args[0] if args else DEFAULT_DATA, with_feedback="--with-feedback" in sys.argv)
