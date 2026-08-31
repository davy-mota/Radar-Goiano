import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
os.environ.setdefault("DATABASE_URL", "sqlite://")
