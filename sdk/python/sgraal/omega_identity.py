"""Omega-Identity NER — regex entity extraction."""
from __future__ import annotations
import re

PRICE_RE = re.compile(r'\$[\d,]+\.?\d*')
DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')
PERSON_RE = re.compile(r'(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+')

def extract_entities(entries):
    prices, dates, persons = set(), set(), set()
    for e in entries:
        c = e.get("content", "")
        prices.update(PRICE_RE.findall(c))
        dates.update(DATE_RE.findall(c))
        persons.update(PERSON_RE.findall(c))
    conflicts = []
    if len(prices) > 1: conflicts.append({"type": "price", "values": list(prices), "conflict": True})
    if len(dates) > 1: conflicts.append({"type": "date", "values": list(dates), "conflict": True})
    if len(persons) > 1: conflicts.append({"type": "person", "values": list(persons), "conflict": True})
    return conflicts
