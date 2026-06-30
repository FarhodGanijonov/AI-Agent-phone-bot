"""
Markazlashgan konfiguratsiya moduli.
Bu modul har doim boshqa app.* modullaridan OLDIN import qilinishi kerak,
chunki u .env faylni yuklaydi va boshqa modullar os.getenv() ni
import vaqtida chaqiradi.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://phonebot:phonebot@localhost:5432/phonebot",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN .env faylda topilmadi.")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY .env faylda topilmadi.")
