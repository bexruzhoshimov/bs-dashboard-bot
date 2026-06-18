import requests
from datetime import datetime
from config import GROQ_API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID, TOPICS


def get_weather_ai():
    lat, lon = 41.2323, 69.1726
    r = requests.get(f"https://wttr.in/{lat},{lon}?format=j1", timeout=10)
    data = r.json()

    current = data["current_condition"][0]
    today = data["weather"][0]

    weather_data = {
        "harorat": current["temp_C"],
        "his_qilish": current["FeelsLikeC"],
        "min": today["mintempC"],
        "max": today["maxtempC"],
        "namlik": current["humidity"],
        "shamol": current["windspeedKmph"],
        "holat": current["weatherDesc"][0]["value"],
        "uv": current["uvIndex"],
        "yomgir_ehtimoli": today["hourly"][4]["chanceofrain"],
        "quyosh_chiqish": today["astronomy"][0]["sunrise"],
        "quyosh_botish": today["astronomy"][0]["sunset"],
    }

    bugun = datetime.now().strftime("%d-%B, %A")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""Quyidagi ob-havo ma'lumotlari asosida qisqa xabar yoz:
Sana: {bugun}
Harorat: {weather_data['harorat']}°C (shamol va namlik sababli {weather_data['his_qilish']}°C kabi seziladi)
Min/Max: {weather_data['min']}°C / {weather_data['max']}°C
Holat: {weather_data['holat']}
Namlik: {weather_data['namlik']}%
Shamol: {weather_data['shamol']} km/h
UV indeks: {weather_data['uv']}
Yomg'ir ehtimoli: {weather_data['yomgir_ehtimoli']}%
Quyosh chiqishi: {weather_data['quyosh_chiqish']}
Quyosh botishi: {weather_data['quyosh_botish']}

Faqat shu formatda yoz, o'zgartirma:
📅 Sana: [bugungi sana va kun nomi o'zbek tilida]
🌡 Harorat: [hozir necha daraja, bugun min-max, tashqarida qanday seziladi]
👕 Kiyim: [nima kiyish kerak aniq]
🏃 Faoliyat: [bugun tashqarida nima qilsa bo'ladi]
💧 Maslahat: [bitta foydali maslahat]
☔ Yomg'ir: [yomg'ir holati]
🌅 Quyosh: [{weather_data['quyosh_chiqish']} da chiqadi, {weather_data['quyosh_botish']} da botadi]

MUHIM: Faqat yuqoridagi formatda yoz. Hech qanday qo'shimcha gap yozma."""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "Sen o'zbek tilida yozuvchi ob-havo yordamchisan. Faqat to'g'ri o'zbek tilida yoz. Hech qachon boshqa tilda yozma. Berilgan ma'lumotlarni o'zgartirma."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 250,
            "temperature": 0.2
        }
    )

    ai_text = response.json()["choices"][0]["message"]["content"]

    result = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "message_thread_id": TOPICS["ob_havo"],
            "text": f"🌤 <b>Bugungi ob-havo — Sergeli</b>\n\n{ai_text}",
            "parse_mode": "HTML"
        }
    )
    print("Ob-havo yuborildi!" if result.json().get("ok") else f"Xato: {result.json()}")
