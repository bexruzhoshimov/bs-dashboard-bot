import json
import time
from datetime import date

import requests

import db
from config import GROQ_API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID, TOPICS

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TASK_THREAD = TOPICS["bugungi_vazifalar"]
GOAL_THREAD = TOPICS["haftalik_maqsadlar"]


def send(thread_id, text):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": CHAT_ID,
        "message_thread_id": thread_id,
        "text": text,
        "parse_mode": "HTML",
    })


def transcribe_voice(file_id):
    file_info = requests.get(f"{API}/getFile", params={"file_id": file_id}).json()
    file_path = file_info["result"]["file_path"]
    audio = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}").content

    resp = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        files={"file": ("voice.ogg", audio)},
        data={"model": "whisper-large-v3", "language": "uz"},
    )
    return resp.json().get("text", "").strip()


def parse_task(text):
    today = date.today().isoformat()
    prompt = f"""Bugungi sana: {today} (Asia/Tashkent). Foydalanuvchi vazifa yozdi: "{text}"

Shu vazifani JSON formatda chiqar, hech qanday qo'shimcha matn yozma:
{{"title": "vazifa nomi", "date": "YYYY-MM-DD", "time": "HH:MM yoki null"}}

Agar sana aytilmagan bo'lsa, bugungi sanani ishlat. Agar vaqt aytilmagan bo'lsa, time ni null qil. O'ylab topma, faqat berilgan matndan foydalan."""

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Sen JSON qaytaradigan yordamchisan. Faqat JSON qaytar, boshqa hech narsa yozma."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 150,
            "temperature": 0,
        },
    )
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    raw = raw.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(raw)
        if "title" not in data or "date" not in data:
            return None
        return data
    except (json.JSONDecodeError, KeyError):
        return None


def handle_task_message(text):
    parsed = parse_task(text)
    if not parsed:
        send(TASK_THREAD, "Tushunmadim, qaytadan aniqroq yozing iltimos.")
        return

    title = parsed["title"]
    task_date = parsed["date"]
    task_time = parsed.get("time")

    event_id, event_link = None, None
    try:
        import calendar_api
        event_id, event_link = calendar_api.create_event(title, task_date, task_time)
    except Exception as e:
        print(f"Calendar xato: {e}")

    db.add_task(title, task_date, task_time, event_id, event_link)

    reply = f"✅ <b>Vazifa qo'shildi</b>\n{title}\n📅 {task_date}"
    if task_time:
        reply += f" ⏰ {task_time}"
    if event_link:
        reply += f"\n<a href=\"{event_link}\">Calendar'da ochish</a>"
    send(TASK_THREAD, reply)


def handle_goal_message(text):
    db.add_goal(text)
    send(GOAL_THREAD, "✅ Maqsad saqlandi")


def process_update(update):
    msg = update.get("message")
    if not msg:
        return
    if msg.get("chat", {}).get("id") != CHAT_ID:
        return

    thread_id = msg.get("message_thread_id")
    text = msg.get("text")
    voice = msg.get("voice")

    if thread_id not in (TASK_THREAD, GOAL_THREAD):
        return

    if voice:
        text = transcribe_voice(voice["file_id"])
        if not text:
            send(thread_id, "Ovozli xabarni tushunolmadim.")
            return

    if not text:
        return

    if thread_id == TASK_THREAD:
        handle_task_message(text)
    elif thread_id == GOAL_THREAD:
        handle_goal_message(text)


def main():
    db.init_db()
    offset = db.get_offset()
    print("Listener ishga tushdi...")
    while True:
        try:
            resp = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=40)
            updates = resp.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                process_update(update)
                db.set_offset(offset)
        except requests.exceptions.RequestException as e:
            print(f"Tarmoq xato: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
