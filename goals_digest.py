from datetime import date, timedelta

import requests

import db
from config import TELEGRAM_BOT_TOKEN, CHAT_ID, TOPICS

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
GOAL_THREAD = TOPICS["haftalik_maqsadlar"]


def main():
    db.init_db()
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    last_week_start = (this_monday - timedelta(days=7)).isoformat()

    goals = db.get_week_goals(last_week_start)
    if not goals:
        text = "O'tgan hafta hech qanday maqsad yozilmagan."
    else:
        lines = "\n".join(f"• {g['text']}" for g in goals)
        text = f"📊 <b>O'tgan hafta maqsadlari:</b>\n{lines}\n\nQaysilarini bajardingiz? Javob yozing."

    result = requests.post(f"{API}/sendMessage", json={
        "chat_id": CHAT_ID,
        "message_thread_id": GOAL_THREAD,
        "text": text,
        "parse_mode": "HTML",
    })
    print("Hisobot yuborildi!" if result.json().get("ok") else f"Xato: {result.json()}")


if __name__ == "__main__":
    main()
