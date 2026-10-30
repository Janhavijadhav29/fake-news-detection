"""
Explainability helpers:
  - key_words(): which words pushed the prediction towards FAKE or REAL
  - red_flags(): simple writing-style signals often seen in fake news
  - fetch_article(): download and extract text from a news URL
"""
import re

import requests
from bs4 import BeautifulSoup

from preprocess import clean_text

CLICKBAIT = [
    "shocking", "breaking", "secret", "miracle", "you won't believe", "share", "forward",
    "viral", "exposed", "hidden truth", "they don't want", "cure", "100%", "guaranteed",
    "click here", "urgent", "must watch", "unbelievable", "hoax", "leaked",
]


def _fake_prob(model, text):
    classes = list(model.classes_)
    return model.predict_proba([text])[0][classes.index("FAKE")]


def key_words(model, raw_text, top_n=8):
    """Leave-one-word-out: how much does removing each word change P(FAKE)?"""
    cleaned = clean_text(raw_text)
    words = cleaned.split()
    if not words:
        return []
    base = _fake_prob(model, cleaned)
    impacts = {}
    for w in list(dict.fromkeys(words))[:60]:
        reduced = " ".join(x for x in words if x != w)
        impacts[w] = base - _fake_prob(model, reduced)   # >0 means word pushes to FAKE
    ranked = sorted(impacts.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_n]
    return [
        {"word": w, "impact": round(v * 100, 2), "towards": "FAKE" if v > 0 else "REAL"}
        for w, v in ranked if abs(v) > 0.0001
    ]


def red_flags(raw_text):
    text = raw_text or ""
    lower = text.lower()
    flags = []
    found = [w for w in CLICKBAIT if w in lower]
    if found:
        flags.append(f"Sensational / clickbait words: {', '.join(found[:6])}")
    if text.count("!") >= 2:
        flags.append(f"Many exclamation marks ({text.count('!')})")
    caps = re.findall(r"\b[A-Z]{4,}\b", text)
    if len(caps) >= 2:
        flags.append(f"Lots of ALL-CAPS words ({len(caps)})")
    if re.search(r"(share|forward) (this|it|to)", lower):
        flags.append("Asks readers to share/forward the message")
    if not re.search(r"\b(said|according to|reported|officials?|study|source)\b", lower):
        flags.append("No source or attribution mentioned")
    if len(text.split()) < 15:
        flags.append("Very short text — prediction is less reliable")
    return flags


def text_stats(raw_text):
    words = raw_text.split()
    sentences = [s for s in re.split(r"[.!?]+", raw_text) if s.strip()]
    return {
        "words": len(words),
        "sentences": len(sentences),
        "reading_time_sec": max(1, round(len(words) / 200 * 60)),
    }


def fetch_article(url, timeout=10):
    if not re.match(r"^https?://", url or ""):
        raise ValueError("Please enter a valid URL starting with http:// or https://")
    headers = {"User-Agent": "Mozilla/5.0 (FakeNewsDetector student project)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    body = " ".join(p for p in paragraphs if len(p) > 40)
    text = f"{title}. {body}".strip()
    if len(text) < 50:
        raise ValueError("Could not extract enough article text from this page.")
    return {"title": title, "text": text[:20000]}
