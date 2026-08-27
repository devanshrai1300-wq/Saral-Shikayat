from datetime import datetime, timedelta
from src.config import DEPARTMENTS

def classify(text: str):
    text_l = text.lower()
    best_key, best_score = "other", 0
    for key, info in DEPARTMENTS.items():
        score = sum(1 for kw in info["keywords"] if kw in text_l)
        if score > best_score:
            best_key, best_score = key, score
    return best_key

def build_sla_dates(department_key: str, start: datetime):
    info = DEPARTMENTS.get(department_key, DEPARTMENTS["other"])
    out = []
    for label, days in info["sla"]:
        out.append({
            "label": label,
            "days": days,
            "date": (start + timedelta(days=days)).strftime("%d %b %Y"),
        })
    return out