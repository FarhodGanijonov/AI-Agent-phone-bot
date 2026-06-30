import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# app.config birinchi import qilinishi SHART — u .env ni yuklaydi.
# Boshqa app.* modullar import vaqtida shu o'zgaruvchilarga tayanadi.
from app.config import TELEGRAM_BOT_TOKEN
from app.agent import ask_agent
from app.db import init_db
from app.seed import seed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men telefon tanlashda yordam beruvchi AI-botman.\n"
        "Masalan: \"200 dollar atrofida kamerasi yaxshi telefon kerak\" deb yozing."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.chat.send_action(action="typing")
    try:
        reply = await ask_agent(user_text)
    except Exception:
        logger.exception("Agent so'rovni qayta ishlashda xatolik yuz berdi")
        reply = "Kechirasiz, xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
    await update.message.reply_text(reply)


def main():
    init_db()
    seed()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
