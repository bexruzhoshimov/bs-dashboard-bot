from weather import get_weather_ai
from news import get_full_news
from finance import get_moliya
from gmail_digest import get_gmail_digest

print("🚀 B's Dashboard Bot ishga tushdi...")

print("\n🌤 Ob-havo...")
get_weather_ai()

print("\n📰 Yangiliklar...")
get_full_news()

print("\n💰 Moliya...")
get_moliya()

print("\n📬 Gmail...")
get_gmail_digest()

print("\n✅ Hammasi yuborildi!")
