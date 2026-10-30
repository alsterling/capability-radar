"""Candidate model: enums, normalization and dedupe keys."""

import json
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

UNKNOWN = "UNKNOWN"
# KEEP: already owned and still adequate; nothing new to adopt. USE: newly adopt or start using.
RECOMMENDATIONS = ("USE", "TEST", "WATCH", "IGNORE", "KEEP")
TRI = ("YES", "NO", UNKNOWN)
NATIVE_OVERLAP = ("YES", "PARTIAL", "NO", UNKNOWN)
EVIDENCE = ("STRONG", "MODERATE", "WEAK", "ANECDOTAL", UNKNOWN)
TIERS = ("TIER1_OFFICIAL", "TIER2_ECOSYSTEM", "TIER3_PRACTICAL", UNKNOWN)
STATUS = ("ACTIVE", "MAINTAINED", "PREVIEW", "STALE", "ARCHIVED", "DEPRECATED", UNKNOWN)
RELATIONS = ("REPLACES", "COMPLEMENTS", "DUPLICATES", "BEATS", "LOSES_TO", UNKNOWN)
SOURCE_TYPES = ("docs", "changelog", "registry", "repo", "benchmark", "review", "news", "forum", "social", "other")

ENUM_FIELDS = {
    "recommendation": RECOMMENDATIONS,
    "improvement_opportunity": TRI,
    "benchmark_needed": TRI,
    "native_overlap": NATIVE_OVERLAP,
    "evidence_quality": EVIDENCE,
    "status": STATUS,
    "owned": TRI,
}
# capability: the job/capability the candidate provides, separate from the product name. Supplied by the
# scan; when missing it stays UNKNOWN (the CLI never infers one).
TEXT_FIELDS = ("capability", "job", "description", "cost", "privacy", "permissions", "reason", "version",
               "evidence_notes", "reverify_trigger", "maintenance_notes")
DATE_FIELDS = ("last_activity", "last_verified", "reverify_after")

# Words that do not distinguish one tool from another ("Acme MCP server" == "Acme").
GENERIC_TOKENS = {"the", "official", "server", "servers", "mcp", "plugin", "plugins", "skill", "skills",
                  "app", "tool", "tools", "ai", "agent", "connector", "extension", "for", "by", "and"}
TRACKING_PARAMS = re.compile(r"^(utm_.*|ref|ref_src|source|fbclid|gclid)$", re.I)

PKG_DATA = Path(__file__).resolve().parent / "data"


def load_categories(config=None):
    """Categories from a workspace config if it defines them, else the packaged defaults."""
    if config and config.get("categories"):
        return config["categories"]
    return json.loads((PKG_DATA / "categories.json").read_text(encoding="utf-8"))["categories"]


def resolve_category(value, categories):
    v = str(value or "").strip().lower()
    for c in categories:
        if v in {c["id"].lower(), c["label"].lower(), *(a.lower() for a in c.get("aliases", []))}:
            return c["id"]
    raise ValueError(f"unknown category {value!r}; known: {', '.join(c['id'] for c in categories)}")


def category_by_id(categories, cid):
    return next(c for c in categories if c["id"] == cid)


def parse_date(value):
    if not value or value == UNKNOWN:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def enum_value(value, allowed):
    if value is None or value == "":
        return UNKNOWN
    v = re.sub(r"[\s\-]+", "_", str(value).strip().upper())
    aliases = {"TIER1": "TIER1_OFFICIAL", "OFFICIAL": "TIER1_OFFICIAL", "TIER2": "TIER2_ECOSYSTEM",
               "ECOSYSTEM": "TIER2_ECOSYSTEM", "TIER3": "TIER3_PRACTICAL", "PRACTICAL": "TIER3_PRACTICAL",
               "TRUE": "YES", "FALSE": "NO", "Y": "YES", "N": "NO"}
    v = aliases.get(v, v)
    return v if v in allowed else None


def normalize_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    s = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(s.query) if not TRACKING_PARAMS.match(k)])
    path = s.path.rstrip("/")
    return urlunsplit((s.scheme.lower(), s.netloc.lower().removeprefix("www."), path, query, ""))


def url_domain(url):
    return urlsplit(url).netloc.lower()


def repo_key(url):
    """github.com/owner/repo for any URL inside a GitHub repo, else None."""
    s = urlsplit(normalize_url(url))
    if s.netloc != "github.com":
        return None
    parts = [p for p in s.path.split("/") if p]
    if len(parts) < 2:
        return None
    return f"github.com/{parts[0].lower()}/{parts[1].lower().removesuffix('.git')}"


def name_key(name):
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\(.*?\)", " ", text)
    tokens = re.findall(r"[a-z0-9]+", text)
    kept = [t for t in tokens if t not in GENERIC_TOKENS]
    return " ".join(kept or tokens)


def words_key(text):
    """Every word, lowercased: case, accents, spacing and punctuation do not matter."""
    return " ".join(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", str(text)).lower()))


def capability_key(text):
    """Grouping key for a capability, or None if unknown."""
    return None if text in (None, "", UNKNOWN) else (words_key(text) or None)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def best_tier(sources):
    tiers = {s.get("tier") for s in sources}
    return next((t for t in TIERS if t in tiers), UNKNOWN)


def _list(value):
    if value is None or value == "" or value == UNKNOWN:
        return []
    return [value] if isinstance(value, (str, dict)) else list(value)


def normalize_sources(raw, warnings):
    out, seen = [], set()
    for s in _list(raw):
        s = {"url": s} if isinstance(s, str) else dict(s)
        url = normalize_url(s.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        tier = enum_value(s.get("tier"), TIERS)
        if tier is None:
            warnings.append(f"source tier {s.get('tier')!r} -> UNKNOWN")
            tier = UNKNOWN
        stype = str(s.get("type") or "other").lower()
        out.append({"url": url, "tier": tier, "type": stype if stype in SOURCE_TYPES else "other",
                    "accessed": s.get("accessed") or UNKNOWN, "note": s.get("note") or ""})
    return out


def normalize_candidate(raw, categories, scan_date=None):
    """Return (candidate, warnings). Raises ValueError when name or category is unusable.

    Missing fields become UNKNOWN, never guesses. Two values are derived by policy, and marked so:
    last_verified defaults to the scan date when the candidate carries at least one source, and
    reverify_after defaults to last_verified + the category's freshness window.
    """
    if not isinstance(raw, dict):
        raise ValueError("candidate must be an object")
    name = str(raw.get("name") or "").strip()
    if not name:
        raise ValueError("candidate has no name")
    category = resolve_category(raw.get("category"), categories)
    warnings = []
    c = {"name": name, "category": category}
    for f in TEXT_FIELDS:
        v = raw.get(f)
        if isinstance(v, (list, tuple)):
            v = "; ".join(str(x) for x in v)
        c[f] = str(v).strip() if v not in (None, "") else UNKNOWN
    for f, allowed in ENUM_FIELDS.items():
        v = enum_value(raw.get(f), allowed)
        if v is None:
            warnings.append(f"{f} {raw.get(f)!r} -> UNKNOWN")
            v = UNKNOWN
        c[f] = v
    if c["recommendation"] == UNKNOWN:
        c["recommendation"] = None  # derived by rank.evaluate
    for f in DATE_FIELDS:
        d = parse_date(raw.get(f))
        if raw.get(f) not in (None, "", UNKNOWN) and d is None:
            warnings.append(f"{f} {raw.get(f)!r} is not an ISO date -> UNKNOWN")
        c[f] = d.isoformat() if d else UNKNOWN
    c["sources"] = normalize_sources(raw.get("sources"), warnings)
    c["source_tier"] = best_tier(c["sources"])
    # The candidate's own repo only: a shared list/registry page it is cited from must not merge tools.
    repo = repo_key(raw.get("repo") or "") or next(
        (repo_key(s["url"]) for s in c["sources"] if s["type"] == "repo" and repo_key(s["url"])), None)
    c["repo"] = repo
    pop = raw.get("popularity")
    c["popularity"] = pop if isinstance(pop, dict) else ({"signal": str(pop)} if pop else {})
    c["aliases"] = sorted({str(a).strip() for a in _list(raw.get("aliases")) if str(a).strip() and str(a).strip() != name})
    c["overlaps_with"] = sorted({str(a).strip() for a in _list(raw.get("overlaps_with")) if str(a).strip()})
    c["duplicate_of"] = str(raw.get("duplicate_of") or "").strip() or None
    ct = raw.get("current_tool")
    if isinstance(ct, dict) and ct.get("name"):
        rel = enum_value(ct.get("relation"), RELATIONS) or UNKNOWN
        c["current_tool"] = {"name": str(ct["name"]), "relation": rel}
    else:
        c["current_tool"] = None
    c["derived"] = []
    if c["last_verified"] == UNKNOWN and c["sources"] and scan_date:
        c["last_verified"] = str(scan_date)
        c["derived"].append("last_verified=scan_date")
    lv = parse_date(c["last_verified"])
    if c["reverify_after"] == UNKNOWN and lv:
        days = category_by_id(categories, category).get("freshness_days", 30)
        c["reverify_after"] = (lv + timedelta(days=days)).isoformat()
        c["derived"].append(f"reverify_after=last_verified+{days}d")
    c["id"] = f"{category}/{slug(name_key(name)) or slug(name)}"
    return c, warnings


def candidate_keys(c):
    """Every key that identifies this candidate inside its category."""
    keys = {f"name:{name_key(c['name'])}"}
    keys |= {f"name:{name_key(a)}" for a in c.get("aliases", [])}
    if c.get("repo"):
        keys.add(f"repo:{c['repo']}")
    return {k for k in keys if k != "name:"}
