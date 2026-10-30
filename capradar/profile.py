"""Editable Markdown profile: who the radar is for, their jobs, current stack and constraints.

Format (all sections optional):

    # <profile name>
    ## Jobs
    - one recurring job per bullet
    ## Current stack
    - Name | category | what it covers (comma-separated)
    ## Constraints
    - free text
"""

import re
from pathlib import Path

from .core import name_key

STOPWORDS = {"with", "that", "this", "from", "into", "about", "your", "their", "them", "they", "have", "what",
             "when", "where", "which", "while", "would", "could", "should", "using", "make", "more", "less",
             "than", "over", "under", "each", "every", "some", "other", "just", "only", "also", "then",
             "very", "much", "many", "most", "work", "things", "thing", "stuff", "weekly", "daily"}


def parse(text):
    prof = {"name": "profile", "jobs": [], "stack": [], "constraints": [], "notes": []}
    section = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# ") and not s.startswith("## "):
            prof["name"] = s[2:].strip()
        elif s.startswith("## "):
            title = s[3:].strip().lower()
            section = ("jobs" if "job" in title else "stack" if "stack" in title
                       else "constraints" if "constraint" in title else "notes")
        elif s.startswith(("- ", "* ")) and section:
            item = s[2:].strip()
            if not item or item.startswith("<"):
                continue
            if section == "stack":
                parts = [p.strip() for p in item.split("|")]
                prof["stack"].append({
                    "name": parts[0],
                    "category": parts[1] if len(parts) > 1 and parts[1] else None,
                    "covers": [c.strip() for c in parts[2].split(",") if c.strip()] if len(parts) > 2 else [],
                })
            else:
                prof[section].append(item)
    return prof


def load(path):
    p = Path(path)
    return parse(p.read_text(encoding="utf-8")) if p.exists() else parse("")


def job_keywords(prof):
    words = set()
    for j in prof["jobs"]:
        words |= {w for w in re.findall(r"[a-z0-9]+", j.lower()) if len(w) >= 4 and w not in STOPWORDS}
    return words


def stack_keys(prof):
    """name_key -> stack item, including what each item covers."""
    return {name_key(s["name"]): s for s in prof["stack"] if name_key(s["name"])}
