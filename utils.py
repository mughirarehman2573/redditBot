import re, random

LINK_RE = re.compile(r"https?://|www\.", re.IGNORECASE)

def no_links(text: str) -> bool:
    return not LINK_RE.search(text or "")

def clamp_sentences(text: str, max_sentences: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:max_sentences])

def jitter_minutes_range(spec: str, default=(20,60)) -> int:
    if isinstance(spec, int):
        return spec
    if isinstance(spec, str) and "-" in spec:
        lo, hi = spec.split("-", 1)
        try:
            return random.randint(int(lo), int(hi))
        except:
            return random.randint(*default)
    return random.randint(*default)

