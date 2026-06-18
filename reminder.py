import requests

import db
from config import TELEGRAM_BOT_TOKEN, CHAT_ID, TOPICS

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TASK_THREAD = TOPICS["bugungi_vazifalar"]


def main():
    db.init_db()
    due = db.get_due_reminders(window_minutes=30)
    for task in due:
        text = f"⏰ <b>Eslatma:</b> {task['title']} — soat {task['time']} da"
        result = requests.post(f"{API}/sendMessage", json={
            "chat_id": CHAT_ID,
            "message_thread_id": TASK_THREAD,
            "text": text,
            "parse_mode": "HTML",
        })
        if result.json().get("ok"):
            db.mark_reminded(task["id"])
            print(f"Eslatma yuborildi: {task['title']}")
        else:
            print(f"Xato: {result.json()}")


if __name__ == "__main__":
    main()
