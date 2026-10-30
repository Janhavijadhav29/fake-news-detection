"""Text cleaning used by both training and prediction."""
import re
import string

# Small built-in English stopword list (avoids an NLTK download step).
STOPWORDS = set("""
a about above after again against all am an and any are as at be because been before being below
between both but by can did do does doing down during each few for from further had has have having
he her here hers herself him himself his how i if in into is it its itself just me more most my
myself no nor not now of off on once only or other our ours ourselves out over own same she should
so some such than that the their theirs them themselves then there these they this those through to
too under until up very was we were what when where which while who whom why will with you your
yours yourself yourselves
""".split())


def clean_text(text: str) -> str:
    """Lowercase, strip URLs/punctuation/digits and remove stopwords."""
    text = str(text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"<.*?>", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\d+", " ", text)
    words = [w for w in text.split() if w not in STOPWORDS and len(w) > 1]
    return " ".join(words)
