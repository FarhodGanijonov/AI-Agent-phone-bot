# 📱 Phone Recommender Telegram Bot (AI Agent)

Foydalanuvchi tabiiy tilda ("200 dollar atrofida kamerasi yaxshi telefon kerak")
yozadi — LLM (Claude) **tool use** orqali Postgres bazasidan mos telefonlarni
filtrlab qidiradi va natijani inson tilida tushuntirib beradi.

## Arxitektura
```
Telegram User -> Bot (python-telegram-bot)
              -> AI Agent (Claude, tool_use: search_phones)
              -> Postgres DB (SQLAlchemy)
```

LLM o'zi qaror qiladi: qaysi filtrlarni qo'llash kerakligini (narx oralig'i,
brend, RAM, kamera) — bu klassik "if/else" emas, balki **AI agent** mantig'i:
model so'rovni tahlil qiladi, kerakli tool'ni (`search_phones`) chaqiradi,
natijani oladi va tabiiy javob shakllantiradi.

## Ishga tushirish

1. `.env.example` faylini `.env` ga nusxalang va tokenlarni kiriting:
   - `TELEGRAM_BOT_TOKEN` — @BotFather orqali olinadi
   - `ANTHROPIC_API_KEY` — console.anthropic.com dan olinadi

2. Docker bilan:
   ```bash
   docker compose up --build
   ```
   Bot avtomatik ravishda bazani yaratadi va namuna telefonlar bilan to'ldiradi.

3. Lokal (Docker'siz):
   ```bash
   pip install -r requirements.txt
   docker run -d -p 5432:5432 -e POSTGRES_USER=phonebot -e POSTGRES_PASSWORD=phonebot -e POSTGRES_DB=phonebot postgres:16-alpine
   python -m app.bot
   ```

## Loyiha tuzilmasi
```
app/
  db.py      # SQLAlchemy model (Phone) va ulanish
  seed.py    # Namuna ma'lumotlar bilan to'ldirish
  agent.py   # LLM + tool_use orqali AI-agent mantig'i
  bot.py     # Telegram bot entrypoint
Dockerfile
docker-compose.yml
requirements.txt
```

## Kengaytirish g'oyalari
- Telefonlar bazasini real do'kon API/parser orqali yangilab turish
- Suhbat tarixini saqlash (context bilan multi-turn savol-javob)
- Inline tugmalar bilan "Batafsil", "O'xshashlarini ko'rsat"
- Admin panel orqali narxlarni yangilash
