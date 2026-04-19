import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
DOCS_DIR = ROOT / "docs"
ITEMS_PATH = DOCS_DIR / "items.json"

FEED_URL = "https://feeds.megaphone.fm/trapdraw"
CHOP_TITLE_RE = r"^(\d+):\s*Chop Session"
TARGET_YEAR = 2026

ANTHROPIC_MODEL = "claude-opus-4-7"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
