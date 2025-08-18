import yaml, pathlib
from pydantic import BaseModel
from typing import List, Dict, Any

class Niche(BaseModel):
    name: str
    subreddits: List[str]
    comment_style: Dict[str, Any] = {}
    prompts: List[str]
    filters: Dict[str, Any] = {}
    posting: Dict[str, Any] = {}
    review_mode: str = "approve_in_ui"

def load_niche(name: str) -> Niche:
    p = pathlib.Path("niches") / f"{name}.yaml"
    data = yaml.safe_load(p.read_text())
    return Niche(**data)
