import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
CHAT_ID = -1004308412289
TOPICS = {
    "yangiliklar":          41,
    "moliya":               42,
    "musiqa_tavsiya":       43,
    "ob_havo":              44,
    "bugungi_vazifalar":    45,
    "haftalik_maqsadlar":   46,
    "bot_bilan_gaplashish": 105
}