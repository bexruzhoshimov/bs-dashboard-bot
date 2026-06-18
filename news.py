import requests
import feedparser
from datetime import datetime, timedelta
from config import GROQ_API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID, TOPICS


def get_full_news():
    bugun = datetime.now()
    bugun_str = bugun.strftime("%d-%m-%Y")
    oy = bugun.strftime("%m")
    kun = bugun.strftime("%d")
    yesterday = (bugun - timedelta(days=1)).strftime("%Y%m%d")
    today = bugun.strftime("%Y%m%d")

    # === RSS ===
    feeds = [
        ("Kun.uz", "UZ", "https://kun.uz/uz/rss"),
        ("Gazeta.uz", "UZ", "https://www.gazeta.uz/rss/"),
        ("Daryo.uz", "UZ", "https://daryo.uz/feed"),
        ("BBC Uzbek", "UZ", "https://feeds.bbci.co.uk/uzbek/rss.xml"),
        ("BBC World", "WORLD", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "WORLD", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("Reuters", "WORLD", "https://feeds.reuters.com/reuters/topNews"),
    ]

    uz_news = []
    world_news = []
    for source, category, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                if category == "UZ":
                    uz_news.append(f"[{source}] {entry.title}")
                else:
                    world_news.append(f"[{source}] {entry.title}")
        except:
            pass

    # === SPORT (kecha + bugun) ===
    try:
        sport_results = []
        for date in [yesterday, today]:
            sport_r = requests.get(
                f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={date}",
                timeout=10
            )
            sport_data = sport_r.json()
            for event in sport_data.get("events", []):
                comp = event["competitions"][0]
                teams = comp["competitors"]
                home = teams[0]["team"]["displayName"]
                away = teams[1]["team"]["displayName"]
                home_score = teams[0].get("score", "-")
                away_score = teams[1].get("score", "-")
                status = event["status"]["type"]["description"]
                line = f"{home} {home_score}:{away_score} {away} ({status})"
                if "Uzbekistan" in home or "Uzbekistan" in away:
                    sport_results.insert(0, "🇺🇿 " + line)
                else:
                    sport_results.append(line)
        sport_text = "\n".join(sport_results[:8])
    except:
        sport_text = "Sport ma'lumotlari yuklanmadi"

    # === TARIX ===
    try:
        wiki_r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{oy}/{kun}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        wiki_data = wiki_r.json()
        events = wiki_data.get("events", [])
        sorted_events = sorted(events, key=lambda x: len(x.get("pages", [])), reverse=True)
        tarix_list = [f"{e['year']}: {e['text']}" for e in sorted_events[:4]]
        tarix_text = "\n".join(tarix_list)
    except:
        tarix_text = "1815: Vaterloo jangi — Napoleon mag'lubiyatga uchradi"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""Bugun {bugun_str}.

O'ZBEKISTON YANGILIKLARI:
{chr(10).join(uz_news[:9])}

JAHON YANGILIKLARI:
{chr(10).join(world_news[:9])}

FIFA WC 2026 NATIJALARI:
{sport_text}

BUGUN TARIXDA (Wikipedia):
{tarix_text}

QAT'IY QOIDALAR:
1. O'zbekiston bo'limida FAQAT O'zbekiston yangiliklari
2. Jahon bo'limida O'zbekiston yangiligi YOZMA
3. Jahon yangiliklar sarlavhalarini o'zbek tiliga tarjima qil
4. Rus, ingliz tilida hech narsa qoldirma
5. Sport bo'limida O'zbekiston o'yinini BIRINCHI yoz
6. Fakt bo'limida yangilik EMAS — ilmiy yoki tarixiy fakt yoz
7. O'ylab topma — faqat berilgan ma'lumotlardan foydalan
8. Takrorlanma — Jahon bo'limida bir xil yangilik ikki marta chiqmasin
9. Imlo: AQSh, Eron, O'zbekiston, Rossiya — to'g'ri yoz

Faqat shu formatda yoz:

🇺🇿 <b>O'zbekiston:</b>
• [yangilik 1]
• [yangilik 2]
• [yangilik 3]

🌍 <b>Jahon:</b>
• [yangilik 1]
• [yangilik 2]
• [yangilik 3]

⚽ <b>Sport — FIFA WC 2026:</b>
• [O'zbekiston natijasi BIRINCHI — tahlil bilan]
• [natija 2]
• [natija 3]
• [natija 4]

📅 <b>Bugun tarixda ({kun}-iyun):</b>
• [eng muhim tarixiy voqea — yil va nima bo'lgani aniq]

💡 <b>Bugungi fakt:</b>
• [ilmiy yoki geografik qiziqarli fakt — yangilik emas, o'ylab topma]

🤖 <b>Xulosa:</b>
[2 gapda eng muhim voqealar, takrorlanmasdan]"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": """Sen professional o'zbek tilida yozuvchi yangiliklar tahlilchisisan.
QOIDALAR:
1. Faqat berilgan ma'lumotlardan foydalан
2. Barcha matnlarni to'g'ri o'zbek tiliga tarjima qil
3. Hech qachon rus, ingliz yoki boshqa tilda yozma
4. O'zbekiston bo'limiga faqat O'zbekiston yangiliklari
5. Jahon bo'limiga O'zbekiston yangiligi kirmasin
6. Imlo: AQSh, Eron, Rossiya, O'zbekiston
7. Fakt — yangilik emas
8. Takrorlanma"""
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.2
        }
    )

    ai_text = response.json()["choices"][0]["message"]["content"]

    corrections = {
        "AQS ": "AQSh ",
        "AQS-": "AQSh-",
        "Éron": "Eron",
        "AQSH": "AQSh",
        "Ukrania": "Ukraina",
    }
    for wrong, correct in corrections.items():
        ai_text = ai_text.replace(wrong, correct)

    result = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "message_thread_id": TOPICS["yangiliklar"],
            "text": f"📰 <b>Kunlik Yangiliklar — {bugun_str}</b>\n\n{ai_text}",
            "parse_mode": "HTML"
        }
    )
    print("Yangiliklar yuborildi!" if result.json().get("ok") else f"Xato: {result.json()}")
