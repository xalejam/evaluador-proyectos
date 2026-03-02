"""Generador de IDs de proyecto."""

from __future__ import annotations

import re


def normalize_country(value: str) -> str:
    return (value or "").strip().upper()[:2] or "NA"


def normalize_owner(value: str) -> str:
    clean = re.sub(r"[^A-Z0-9_]", "", (value or "").strip().upper())
    return clean or "GEN"


def build_project_id(country: str, owner: str, sequence: int, n_digits: int = 4, pattern: str = "{country}-{owner}-{sequence}") -> str:
    c = normalize_country(country)
    o = normalize_owner(owner)
    s = f"{int(sequence):0{int(n_digits)}d}"
    return pattern.format(country=c, owner=o, sequence=s)
