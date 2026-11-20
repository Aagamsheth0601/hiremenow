import re


_INDIA_TERMS = (
    "india", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad",
    "pune", "chennai", "gurgaon", "gurugram", "noida", "kolkata",
    "ahmedabad", "jaipur",
)
_US_TERMS = (
    "united states", "usa", "u.s.", "san francisco", "new york", "nyc",
    "los angeles", "boston", "seattle", "chicago", "austin", "denver",
    "miami", "atlanta", "dallas", "houston", "san jose", "palo alto",
    "mountain view", "menlo park", "berkeley", "oakland", "sunnyvale",
    "santa clara", "redwood city", "cambridge",
)
_US_STATE_RE = re.compile(r",\s*[A-Z]{2}\b")


def matches_region(locations: list[str], region: str, *, title: str = "") -> bool:
    blob = " ".join(locations or []).lower()
    if title:
        blob += " " + title.lower()
    raw = " ".join(locations or []) + " " + title
    is_india = any(t in blob for t in _INDIA_TERMS) or bool(re.search(r"\bIN\b", raw))
    is_us = any(t in blob for t in _US_TERMS) or bool(re.search(r"\b(?:us|usa)\b", blob.replace(".", ""))) or bool(_US_STATE_RE.search(raw))
    is_remote = "remote" in blob
    if is_remote and not is_india and not is_us:
        return True
    if region == "india":
        return is_india
    if region == "us":
        if is_india:
            return False
        return is_us
    return True
