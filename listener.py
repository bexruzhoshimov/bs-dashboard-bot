import json
import time
from datetime import date

import requests

import db
from config import GROQ_API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID, TOPICS

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
HUB_THREAD = TOPICS["bot_bilan_gaplashish"]
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


def classify_message(text):
    """Xabarni vazifa/maqsad/noaniq turlarga ajratadi va kerakli maydonlarni chiqaradi."""
    today = date.today().isoformat()
    prompt = f"""Bugungi sana: {today} (Asia/Tashkent). Foydalanuvchi botga shu xabarni yozdi: "{text}"

Xabar turini aniqla va JSON formatda chiqar, hech qanday qo'shimcha matn yozma:
- Agar bu aniq bir martalik VAZIFA bo'lsa (qilinishi kerak bo'lgan ish, ko'pincha sana/vaqt bilan):
  {{"type": "task", "title": "vazifa nomi", "date": "YYYY-MM-DD", "time": "HH:MM yoki null"}}
- Agar bu HAFTALIK/uzoq muddatli MAQSAD bo'lsa (masalan o'rganish, mashq qilish, odat):
  {{"type": "goal", "text": "maqsad matni"}}
- Agar foydalanuvchi Google Meet/video uchrashuv link so'rasa:
  {{"type": "meet", "title": "uchrashuv nomi (aytilmagan bo'lsa 'Uchrashuv')"}}
- Agar bu vazifa ham, maqsad ham emas, oddiy SAVOL yoki SUHBAT bo'lsa:
  {{"type": "chat"}}
- Agar tushunarsiz bo'lsa:
  {{"type": "unknown"}}

Sana aytilmagan bo'lsa bugungi sanani ishlat. Vaqt aytilmagan bo'lsa time ni null qil. O'ylab topma, faqat berilgan matndan foydalan."""

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
        if data.get("type") not in ("task", "goal", "meet", "chat", "unknown"):
            return None
        return data
    except json.JSONDecodeError:
        return None


def handle_chat(text):
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Sen o'zbek tilida do'stona javob beruvchi yordamchisan. Qisqa va tabiiy javob ber."},
                {"role": "user", "content": text},
            ],
            "max_tokens": 400,
            "temperature": 0.5,
        },
    )
    reply = resp.json()["choices"][0]["message"]["content"].strip()
    send(HUB_THREAD, reply)


def handle_task(data):
    title = data.get("title")
    task_date = data.get("date")
    task_time = data.get("time")
    if not title or not task_date:
        send(HUB_THREAD, "Vazifani tushunolmadim, qaytadan aniqroq yozing iltimos.")
        return

    event_id, event_link = None, None
    try:
        import calendar_api
        event_id, event_link = calendar_api.create_event(title, task_date, task_time)
    except Exception as e:
        print(f"Calendar xato: {e}")

    db.add_task(title, task_date, task_time, event_id, event_link)

    detail = f"✅ <b>Vazifa qo'shildi</b>\n{title}\n📅 {task_date}"
    if task_time:
        detail += f" ⏰ {task_time}"
    if event_link:
        detail += f"\n<a href=\"{event_link}\">Calendar'da ochish</a>"
    send(TASK_THREAD, detail)
    send(HUB_THREAD, f"✅ Qabul qilindi → Bugungi vazifalar: {title}")


def handle_meet(data):
    title = data.get("title") or "Uchrashuv"
    try:
        import calendar_api
        _, meet_link = calendar_api.create_meet(title)
    except Exception as e:
        send(HUB_THREAD, f"Meet yaratishda xato: {e}")
        return

    if meet_link:
        send(HUB_THREAD, f"📹 <b>{title}</b>\n<a href=\"{meet_link}\">{meet_link}</a>")
    else:
        send(HUB_THREAD, "Meet link yaratilmadi, qaytadan urinib ko'ring.")


def handle_goal(data):
    text = data.get("text")
    if not text:
        send(HUB_THREAD, "Maqsadni tushunolmadim, qaytadan aniqroq yozing iltimos.")
        return
    db.add_goal(text)
    send(GOAL_THREAD, f"🎯 {text}")
    send(HUB_THREAD, f"✅ Qabul qilindi → Haftalik maqsadlar: {text}")


def process_update(update):
    msg = update.get("message")
    if not msg:
        return
    if msg.get("chat", {}).get("id") != CHAT_ID:
        return

    thread_id = msg.get("message_thread_id")
    text = msg.get("text")
    voice = msg.get("voice")

    if thread_id in (TASK_THREAD, GOAL_THREAD):
        send(thread_id, "Iltimos, \"Bot bilan gaplashish\" topicda yozing — men shu yerga avtomatik yozaman.")
        return

    if thread_id != HUB_THREAD:
        return

    if voice:
        text = transcribe_voice(voice["file_id"])
        if not text:
            send(HUB_THREAD, "Ovozli xabarni tushunolmadim.")
            return

    if not text:
        return

    parsed = classify_message(text)
    if not parsed:
        send(HUB_THREAD, "Tushunolmadim, qaytadan aniqroq yozing iltimos.")
        return

    if parsed["type"] == "task":
        handle_task(parsed)
    elif parsed["type"] == "goal":
        handle_goal(parsed)
    elif parsed["type"] == "meet":
        handle_meet(parsed)
    elif parsed["type"] == "chat":
        handle_chat(text)
    else:
        send(HUB_THREAD, "Tushunolmadim, qaytadan aniqroq yozing iltimos.")


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
