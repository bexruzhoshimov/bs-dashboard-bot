import base64

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import GROQ_API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID, TOPICS

TOKEN_PATH = "token.json"


def _get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _get_snippet(service, msg_id):
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="metadata",
        metadataHeaders=["From", "Subject"],
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    return {
        "from": headers.get("From", "?"),
        "subject": headers.get("Subject", "(mavzu yo'q)"),
        "snippet": msg.get("snippet", ""),
    }


def get_gmail_digest():
    service = _get_service()
    results = service.users().messages().list(
        userId="me", q="is:important is:unread newer_than:1d", maxResults=10
    ).execute()
    messages = results.get("messages", [])

    if not messages:
        text = "📭 Oxirgi 24 soatda muhim/o'qilmagan xat yo'q."
        result = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "message_thread_id": TOPICS["gmail"], "text": text},
        )
        print("Gmail digest yuborildi!" if result.json().get("ok") else f"Xato: {result.json()}")
        return

    items = [_get_snippet(service, m["id"]) for m in messages]
    items_text = "\n".join(f"- {i['from']}: {i['subject']} — {i['snippet']}" for i in items)

    prompt = f"""Quyidagi muhim va o'qilmagan email'lar ro'yxati:
{items_text}

Har biri uchun qisqa o'zbek tilida xulosa yoz. Faqat shu formatda:
📧 <b>[jo'natuvchi qisqa nomi]</b>: [bir gapda nima haqida]

Boshqa hech narsa qo'shma, o'ylab topma, faqat berilgan ma'lumotdan foydalan."""

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Sen o'zbek tilida email xulosalovchisan. Faqat berilgan ma'lumotdan foydalan, o'ylab topma."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 600,
            "temperature": 0.1,
        },
    )
    ai_text = resp.json()["choices"][0]["message"]["content"]

    result = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "message_thread_id": TOPICS["gmail"],
            "text": f"📬 <b>Gmail — muhim xatlar</b>\n\n{ai_text}",
            "parse_mode": "HTML",
        },
    )
    print("Gmail digest yuborildi!" if result.json().get("ok") else f"Xato: {result.json()}")
