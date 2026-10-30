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

from .core import words_key

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


def stem(word):
    """Crude, deterministic stem: drop one plural "s" (not "ss"), keep the first 6 letters.

    "agents" -> "agent", "documents"/"document" -> "docume", "automation"/"automate" -> "automa".
    """
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word[:6]


def terms(text):
    """Distinctive stemmed terms of a text: words of 4+ letters that are not stopwords."""
    return {stem(w) for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) >= 4 and w not in STOPWORDS}


def job_terms(prof):
    """[(job, its terms)] in profile order; jobs with no distinctive term are skipped."""
    return [(j, t) for j in prof["jobs"] if (t := terms(j))]


def stack_key(name):
    """Strict name key for matching the current stack: every word counts.

    Unlike the dedupe key, generic words are kept, so "Acme MCP Server" is not the stack item "Acme".
    """
    return words_key(name)


def stack_keys(prof):
    """stack_key -> stack item, including what each item covers."""
    return {stack_key(s["name"]): s for s in prof["stack"] if stack_key(s["name"])}
