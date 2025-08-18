import random
from typing import Optional
from utils import clamp_sentences, no_links
from niches import load_niche

FALLBACKS = [
    "Nice take — I'd focus on one small tweak and keep it consistent.",
    "Good point. Small adjustments and patience usually pay off.",
    "Looks solid. Maybe lighten the grip pressure and stay smooth.",
]

def generate_comment(title: str, body: str, niche_name: str = "golf") -> Optional[str]:
    ctx = f"{(title or '')[:200]} {(body or '')[:400]}".strip()
    if not ctx:
        return None

    try:
        niche = load_niche(niche_name)
        prompt = random.choice(niche.prompts) if niche.prompts else "Reply helpfully:"
        # ⚠️ For MVP, keep it simple/local (no API). Later plug OpenAI/Anthropic here.
        text = f"{random.choice(FALLBACKS)}"
    except Exception:
        text = random.choice(FALLBACKS)

    text = clamp_sentences(text, max_sentences=2)
    return text if no_links(text) else None
