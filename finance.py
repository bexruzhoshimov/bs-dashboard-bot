import requests
from datetime import datetime
from config import GROQ_API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID, TOPICS


def get_moliya():
    bugun = datetime.now().strftime("%d-%m-%Y")

    # === CBU KURSLAR ===
    kurslar = {}
    valyutalar = ["USD", "EUR", "RUB", "CNY", "GBP"]
    for val in valyutalar:
        try:
            r = requests.get(f"https://cbu.uz/oz/arkhiv-kursov-valyut/json/{val}/", timeout=5)
            data = r.json()[0]
            rate = float(data['Rate'])
            diff = float(data['Diff'])
            arrow = "📈" if diff > 0 else "📉"
            kurslar[val] = {"rate": rate, "diff": diff, "arrow": arrow}
        except:
            kurslar[val] = None

    # === KRIPTO ===
    try:
        crypto_r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether,the-open-network&vs_currencies=usd&include_24hr_change=true",
            timeout=10
        )
        crypto = crypto_r.json()
        btc = crypto["bitcoin"]["usd"]
        btc_ch = crypto["bitcoin"]["usd_24h_change"]
        eth = crypto["ethereum"]["usd"]
        eth_ch = crypto["ethereum"]["usd_24h_change"]
        usdt = crypto["tether"]["usd"]
        ton = crypto["the-open-network"]["usd"]
        ton_ch = crypto["the-open-network"]["usd_24h_change"]
    except Exception as e:
        print(f"Kripto xato: {e}")
        btc = eth = usdt = ton = 0
        btc_ch = eth_ch = ton_ch = 0

    # === NEFT ===
    try:
        neft_r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=10
        )
        neft_data = neft_r.json()
        neft = neft_data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        neft_prev = neft_data["chart"]["result"][0]["meta"]["previousClose"]
        neft_ch = ((neft - neft_prev) / neft_prev) * 100
        neft_arrow = "📈" if neft_ch > 0 else "📉"
    except:
        neft = None
        neft_ch = 0
        neft_arrow = "➡️"

    # === OLTIN ===
    try:
        oltin_r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=10
        )
        oltin_data = oltin_r.json()
        oltin_oz = oltin_data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        oltin_gram = round(oltin_oz / 31.1035, 2)
        oltin_prev = oltin_data["chart"]["result"][0]["meta"]["previousClose"]
        oltin_ch = ((oltin_oz - oltin_prev) / oltin_prev) * 100
        oltin_arrow = "📈" if oltin_ch > 0 else "📉"
    except:
        oltin_gram = None
        oltin_ch = 0
        oltin_arrow = "➡️"

    def fmt(val, decimals=2):
        if val is None:
            return "N/A"
        return f"{val:,.{decimals}f}"

    def fmt_ch(ch, arrow):
        return f"{arrow} {ch:+.2f}%"

    usd = kurslar.get("USD")
    eur = kurslar.get("EUR")
    rub = kurslar.get("RUB")
    cny = kurslar.get("CNY")
    gbp = kurslar.get("GBP")

    kurs_text = f"""USD: {fmt(usd['rate'], 0)} so'm {usd['arrow']} {usd['diff']:+.2f}
EUR: {fmt(eur['rate'], 0)} so'm {eur['arrow']} {eur['diff']:+.2f}
RUB: {fmt(rub['rate'], 2)} so'm {rub['arrow']} {rub['diff']:+.2f}
CNY: {fmt(cny['rate'], 2)} so'm {cny['arrow']} {cny['diff']:+.2f}
GBP: {fmt(gbp['rate'], 0)} so'm {gbp['arrow']} {gbp['diff']:+.2f}"""

    kripto_text = f"""BTC: ${fmt(btc, 0)} {('📈' if btc_ch>0 else '📉')} {btc_ch:+.2f}%
ETH: ${fmt(eth, 2)} {('📈' if eth_ch>0 else '📉')} {eth_ch:+.2f}%
USDT: ${fmt(usdt, 3)}
TON: ${fmt(ton, 2)} {('📈' if ton_ch>0 else '📉')} {ton_ch:+.2f}%"""

    xomashyo_text = f"""Neft (Brent): ${fmt(neft, 2)}/barrel {fmt_ch(neft_ch, neft_arrow)}
Oltin: ${fmt(oltin_gram, 2)}/gram {fmt_ch(oltin_ch, oltin_arrow)}"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""Bugun {bugun}. Quyidagi moliyaviy ma'lumotlar:

KURSLAR:
{kurs_text}

KRIPTO:
{kripto_text}

XOM ASHYO:
{xomashyo_text}

Faqat shu formatda yoz, o'zbek tilida:

💱 <b>Valyuta kurslari:</b>
• 💵 USD: [rate] so'm [arrow] [diff]
• 💶 EUR: [rate] so'm [arrow] [diff]
• 🇷🇺 RUB: [rate] so'm [arrow] [diff]
• 🇨🇳 CNY: [rate] so'm [arrow] [diff]
• 🇬🇧 GBP: [rate] so'm [arrow] [diff]

₿ <b>Kripto bozori:</b>
• BTC: $[narx] [o'zgarish]
• ETH: $[narx] [o'zgarish]
• USDT: $[narx]
• TON: $[narx] [o'zgarish]

🛢 <b>Xom ashyo:</b>
• Neft (Brent): $[narx]/barrel [o'zgarish]
• Oltin: $[narx]/gram [o'zgarish]

📊 <b>Bugungi tahlil:</b>
[2-3 gap: bozorda nima bo'ldi, nima uchun, oddiy tilda]

💡 <b>Bugungi moliya darsi:</b>
[bugungi bozor holatiga bog'liq ANIQ maslahat]"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "Sen o'zbek tilida moliyaviy tahlilchisan. Faqat berilgan ma'lumotlardan foydalan. Hech narsa o'ylab topma. Faqat o'zbek tilida yoz."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 600,
            "temperature": 0.1
        }
    )

    ai_text = response.json()["choices"][0]["message"]["content"]

    result = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "message_thread_id": TOPICS["moliya"],
            "text": f"💰 <b>Moliya — {bugun}</b>\n\n{ai_text}",
            "parse_mode": "HTML"
        }
    )
    print("Moliya yuborildi!" if result.json().get("ok") else f"Xato: {result.json()}")
