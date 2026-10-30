"""
Flask backend for the Fake News Detection System.

Run:  python backend/app.py   then open http://127.0.0.1:5000
"""
import csv
import io
import json
import os

import joblib
from flask import Flask, Response, jsonify, request, send_from_directory

import analyzer
import database
import train_model
from preprocess import clean_text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
MODEL_PATH = train_model.MODEL_PATH
METRICS_PATH = train_model.METRICS_PATH
MAX_BATCH = 500

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
database.init_db()

if not os.path.exists(MODEL_PATH):
    print("No trained model found - training one now on the sample dataset...")
    train_model.train(verbose=True)
model = joblib.load(MODEL_PATH)


def run_prediction(text, source="text", url=None, explain=True):
    cleaned = clean_text(text)
    probs = model.predict_proba([cleaned])[0]
    classes = list(model.classes_)
    best = int(probs.argmax())
    label = classes[best]
    confidence = round(float(probs[best]) * 100, 2)
    record_id = database.save_prediction(text, label, confidence, source, url)
    result = {
        "id": record_id,
        "prediction": label,
        "confidence": confidence,
        "probabilities": {c: round(float(p) * 100, 2) for c, p in zip(classes, probs)},
    }
    if explain:
        result["key_words"] = analyzer.key_words(model, text)
        result["red_flags"] = analyzer.red_flags(text)
        result["text_stats"] = analyzer.text_stats(text)
    return result


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ---------- prediction ----------
@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if len(text) < 10:
        return jsonify({"error": "Please enter at least 10 characters of news text."}), 400
    return jsonify(run_prediction(text))


@app.route("/api/predict-url", methods=["POST"])
def predict_url():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    try:
        article = analyzer.fetch_article(url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Could not download that page. Check the URL and your internet connection."}), 400
    result = run_prediction(article["text"], source="url", url=url)
    result["article_title"] = article["title"]
    result["article_preview"] = article["text"][:400]
    return jsonify(result)


@app.route("/api/predict-batch", methods=["POST"])
def predict_batch():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Please upload a CSV file."}), 400
    try:
        content = file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return jsonify({"error": "File must be UTF-8 encoded CSV."}), 400
    reader = csv.DictReader(io.StringIO(content))
    col = next((c for c in (reader.fieldnames or []) if c.strip().lower() in ("text", "news", "title", "content")), None)
    if not col:
        return jsonify({"error": "CSV needs a column named 'text' (or 'news', 'title', 'content')."}), 400
    results = []
    for row in reader:
        text = (row.get(col) or "").strip()
        if len(text) < 10:
            continue
        r = run_prediction(text, source="batch", explain=False)
        results.append({"id": r["id"], "text": text[:200], "prediction": r["prediction"], "confidence": r["confidence"]})
        if len(results) >= MAX_BATCH:
            break
    summary = {
        "total": len(results),
        "fake": sum(r["prediction"] == "FAKE" for r in results),
        "real": sum(r["prediction"] == "REAL" for r in results),
    }
    return jsonify({"summary": summary, "results": results})


# ---------- feedback ----------
@app.route("/api/feedback", methods=["POST"])
def feedback():
    data = request.get_json(silent=True) or {}
    pid = data.get("prediction_id")
    is_correct = data.get("is_correct")
    if not isinstance(pid, int) or not isinstance(is_correct, bool):
        return jsonify({"error": "prediction_id (int) and is_correct (bool) are required."}), 400
    if not database.save_feedback(pid, is_correct):
        return jsonify({"error": "Prediction not found."}), 404
    return jsonify({"message": "Thanks for your feedback!"})


# ---------- history ----------
@app.route("/api/history", methods=["GET"])
def history():
    return jsonify(database.get_history(
        limit=min(int(request.args.get("limit", 50)), 500),
        search=request.args.get("search", "").strip(),
        label=request.args.get("label", "").upper(),
    ))


@app.route("/api/history/<int:pid>", methods=["DELETE"])
def delete_one(pid):
    database.delete_prediction(pid)
    return jsonify({"message": "Deleted"})


@app.route("/api/history", methods=["DELETE"])
def clear():
    database.clear_history()
    return jsonify({"message": "History cleared"})


@app.route("/api/export")
def export_csv():
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "news_text", "source", "url", "prediction", "confidence", "created_at"])
    for r in database.get_all_predictions():
        writer.writerow([r["id"], r["news_text"], r["source"], r["url"] or "", r["prediction"], r["confidence"], r["created_at"]])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=prediction_history.csv"})


# ---------- dashboard & model ----------
@app.route("/api/stats")
def stats():
    return jsonify(database.get_stats())


@app.route("/api/model-info")
def model_info():
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH) as f:
            return jsonify(json.load(f))
    return jsonify({"error": "No metrics found. Retrain the model."}), 404


@app.route("/api/retrain", methods=["POST"])
def retrain():
    global model
    metrics = train_model.train(with_feedback=True, verbose=False)
    model = joblib.load(MODEL_PATH)
    return jsonify(metrics)


if __name__ == "__main__":
    app.run(debug=True)
