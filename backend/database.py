"""SQLite helpers: predictions, user feedback and statistics."""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "fake_news.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                news_text   TEXT    NOT NULL,
                source      TEXT    NOT NULL DEFAULT 'text',   -- text | url | batch
                url         TEXT,
                prediction  TEXT    NOT NULL,                   -- REAL | FAKE
                confidence  REAL    NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id  INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
                is_correct     INTEGER NOT NULL,                -- 1 = correct, 0 = wrong
                correct_label  TEXT    NOT NULL,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def save_prediction(text, prediction, confidence, source="text", url=None):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO predictions (news_text, source, url, prediction, confidence) VALUES (?, ?, ?, ?, ?)",
            (text, source, url, prediction, confidence),
        )
        return cur.lastrowid


def get_history(limit=50, search="", label=""):
    sql = (
        "SELECT p.id, p.news_text, p.source, p.url, p.prediction, p.confidence, p.created_at, "
        "f.is_correct FROM predictions p LEFT JOIN feedback f ON f.prediction_id = p.id WHERE 1=1"
    )
    params = []
    if search:
        sql += " AND p.news_text LIKE ?"
        params.append(f"%{search}%")
    if label in ("REAL", "FAKE"):
        sql += " AND p.prediction = ?"
        params.append(label)
    sql += " ORDER BY p.id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_all_predictions():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, news_text, source, url, prediction, confidence, created_at FROM predictions ORDER BY id"
        ).fetchall()]


def get_stats():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(prediction='FAKE') AS fake, SUM(prediction='REAL') AS real, "
            "ROUND(AVG(confidence), 2) AS avg_conf FROM predictions"
        ).fetchone()
        daily = conn.execute(
            "SELECT DATE(created_at) AS day, "
            "SUM(prediction='FAKE') AS fake, SUM(prediction='REAL') AS real "
            "FROM predictions GROUP BY day ORDER BY day DESC LIMIT 14"
        ).fetchall()
        fb = conn.execute(
            "SELECT COUNT(*) AS total, SUM(is_correct) AS correct FROM feedback"
        ).fetchone()
        return {
            "total": row["total"] or 0,
            "fake": row["fake"] or 0,
            "real": row["real"] or 0,
            "avg_confidence": row["avg_conf"] or 0,
            "daily": [dict(d) for d in reversed(daily)],
            "feedback_total": fb["total"] or 0,
            "feedback_correct": fb["correct"] or 0,
        }


def save_feedback(prediction_id, is_correct):
    with get_connection() as conn:
        row = conn.execute("SELECT prediction FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
        if not row:
            return False
        predicted = row["prediction"]
        correct_label = predicted if is_correct else ("REAL" if predicted == "FAKE" else "FAKE")
        conn.execute("DELETE FROM feedback WHERE prediction_id = ?", (prediction_id,))
        conn.execute(
            "INSERT INTO feedback (prediction_id, is_correct, correct_label) VALUES (?, ?, ?)",
            (prediction_id, 1 if is_correct else 0, correct_label),
        )
        return True


def get_feedback_for_training():
    with get_connection() as conn:
        return [tuple(r) for r in conn.execute(
            "SELECT p.news_text, f.correct_label FROM feedback f JOIN predictions p ON p.id = f.prediction_id"
        ).fetchall()]


def delete_prediction(prediction_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM feedback WHERE prediction_id = ?", (prediction_id,))
        conn.execute("DELETE FROM predictions WHERE id = ?", (prediction_id,))


def clear_history():
    with get_connection() as conn:
        conn.execute("DELETE FROM feedback")
        conn.execute("DELETE FROM predictions")
