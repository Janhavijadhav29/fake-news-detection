# Fake News Detection System

A web application that uses **Machine Learning** to classify news headlines and articles as **REAL** or **FAKE**, explains *why*, and stores every check in a database.

**Frontend:** HTML, CSS, JavaScript, Chart.js · **Backend:** Python, Flask, scikit-learn · **Database:** SQLite

---

## Features

| Feature | Description |
|---|---|
| Text check | Paste a headline or article and get REAL / FAKE with confidence |
| Check by URL | Paste a news link — the article text is scraped and analysed |
| Voice input | Speak the news using the browser's speech recognition |
| Batch check | Upload a CSV and classify up to 500 news items at once |
| Explainable AI | Shows the key words that pushed the result towards FAKE or REAL |
| Highlighted text | Influential words highlighted in red / green inside the text |
| Warning signs | Detects clickbait words, ALL-CAPS, "share/forward" requests, missing sources |
| Probability bars | Real vs Fake probability for every prediction |
| User feedback | Mark predictions correct / wrong; stored in SQLite |
| Retrain with feedback | One click retrains the model including user corrections |
| Model comparison | Trains 4 models (Logistic Regression, Naive Bayes, Passive Aggressive, Random Forest) and auto-selects the best by F1-score |
| Dashboard | Totals, average confidence, doughnut chart and daily bar chart |
| History | Search, filter by result, delete single rows, clear all |
| Export | Download full history as CSV |
| Dark mode | Light / dark theme, remembered by the browser |
| Copy result | Copy the prediction to clipboard |
| Responsive | Works on mobile and desktop |

## Project structure

```
fake-news-detection/
├── backend/
│   ├── app.py            # Flask server + REST API
│   ├── train_model.py    # trains & compares ML models
│   ├── preprocess.py     # text cleaning
│   ├── analyzer.py       # key words, warning signs, URL scraping
│   └── database.py       # SQLite (predictions + feedback)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── data/
│   └── sample_news.csv   # small demo dataset
├── model/                # trained model is saved here
└── requirements.txt
```

## How it works

1. **Input** – text, URL, voice or CSV
2. **Preprocessing** – lowercase, remove URLs / punctuation / numbers / stopwords
3. **Vectorization** – TF-IDF (unigrams + bigrams)
4. **Classification** – best of 4 trained models predicts REAL / FAKE
5. **Explanation** – leave-one-word-out analysis finds the most influential words
6. **Storage** – results and feedback saved in SQLite

## Setup & run

```bash
git clone https://github.com/<your-username>/fake-news-detection.git
cd fake-news-detection
pip install -r requirements.txt

python backend/train_model.py     # train the model
python backend/app.py             # start the server
```

Open **http://127.0.0.1:5000** in your browser.

## Using a real dataset (recommended)

`data/sample_news.csv` is a tiny demo dataset (50 rows) so the project runs out of the box — accuracy on it is **not** meaningful.
For real results, download a public dataset such as the Kaggle *Fake and Real News Dataset*, make a CSV with columns `text,label` (`label` = `REAL` or `FAKE`) and train:

```bash
python backend/train_model.py data/news.csv
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/predict` | `{ "text": "..." }` → prediction, probabilities, key words, warning signs |
| POST | `/api/predict-url` | `{ "url": "https://..." }` → same, from a web article |
| POST | `/api/predict-batch` | multipart CSV upload (`text` column) |
| POST | `/api/feedback` | `{ "prediction_id": 1, "is_correct": true }` |
| GET | `/api/history?search=&label=` | saved predictions |
| DELETE | `/api/history` / `/api/history/<id>` | clear all / delete one |
| GET | `/api/export` | download history CSV |
| GET | `/api/stats` | dashboard numbers |
| GET | `/api/model-info` | model comparison metrics |
| POST | `/api/retrain` | retrain including user feedback |

## Database schema (SQLite)

- **predictions** – id, news_text, source (text/url/batch), url, prediction, confidence, created_at
- **feedback** – id, prediction_id, is_correct, correct_label, created_at

## Future scope

- Deep learning models (LSTM / BERT)
- Multilingual support (Hindi, Marathi)
- Browser extension for one-click checking
- User accounts and admin panel

## Author

**Pratik Raut** — [GitHub](https://github.com/pratikraut01) · [LinkedIn](https://linkedin.com/in/pratik-raut123)

> ML predictions can be wrong. Always verify important news with trusted sources.
