import html
import json

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
        "link": f"https://mail.google.com/mail/u/0/#all/{msg_id}",
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
    items_text = "\n".join(f"{idx}. {i['from']}: {i['subject']} — {i['snippet']}" for idx, i in enumerate(items))

    prompt = f"""Quyidagi muhim va o'qilmagan email'lar ro'yxati (raqamlangan):
{items_text}

Har biri uchun bir gapli o'zbek tilida xulosa yoz. Faqat shu JSON formatda chiqar:
{{"summaries": ["[0-raqamli xat xulosasi]", "[1-raqamli xat xulosasi]", ...]}}

Ro'yxat tartibini saqla, har bir elementga mos bitta xulosa. O'ylab topma, faqat berilgan ma'lumotdan foydalan."""

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Sen JSON qaytaradigan email xulosalovchisan. Faqat JSON qaytar, boshqa hech narsa yozma."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 600,
            "temperature": 0.1,
        },
    )
    raw = resp.json()["choices"][0]["message"]["content"].strip().strip("`").removeprefix("json").strip()
    try:
        summaries = json.loads(raw).get("summaries", [])
    except json.JSONDecodeError:
        summaries = []

    blocks = []
    for idx, item in enumerate(items):
        summary = summaries[idx] if idx < len(summaries) else item["subject"]
        sender = html.escape(item["from"])
        blocks.append(
            f"📧 <b>{sender}</b>: {html.escape(summary)}\n🔗 <a href=\"{item['link']}\">Xatni ochish</a>"
        )
    text = "📬 <b>Gmail — muhim xatlar</b>\n\n" + "\n\n".join(blocks)

    result = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "message_thread_id": TOPICS["gmail"],
            "text": text,
            "parse_mode": "HTML",
        },
    )
    print("Gmail digest yuborildi!" if result.json().get("ok") else f"Xato: {result.json()}")
