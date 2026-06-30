"""
AI agent: foydalanuvchi tabiiy tilda yozadi (masalan
"200 dollar atrofida kamerasi yaxshi telefon kerak"),
LLM buni tool-call orqali bazadan filtrlab, natijani
tabiiy tilda izohlab beradi.

Performance eslatmalari:
- AsyncAnthropic ishlatiladi, shunda LLM javobini kutish paytida
  event loop boshqa foydalanuvchilarning xabarlarini parallel qayta ishlay oladi.
- search_phones natijalari Redis'da keshlanadi — bir xil filtrlar bilan
  qaytadan DB so'ralmaydi.
- Sinxron SQLAlchemy chaqiruvi asyncio.to_thread orqali alohida
  thread'da bajariladi, shunda event loop bloklanmaydi.
"""
import asyncio
import json
from anthropic import AsyncAnthropic
from sqlalchemy import and_

from app.config import ANTHROPIC_API_KEY
from app.db import SessionLocal, Phone
from app.cache import get_cached, set_cached

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
MODEL = "claude-sonnet-4-6"
MAX_TOOL_ITERATIONS = 5  # cheksiz tsikldan himoya

SEARCH_TOOL = {
    "name": "search_phones",
    "description": "Bazadan telefonlarni narx, RAM, xotira yoki brend bo'yicha filtrlab qidiradi.",
    "input_schema": {
        "type": "object",
        "properties": {
            "min_price": {"type": "number", "description": "Minimal narx (USD)"},
            "max_price": {"type": "number", "description": "Maksimal narx (USD)"},
            "brand": {"type": "string", "description": "Brend nomi, masalan Samsung, Xiaomi, Apple"},
            "min_camera_mp": {"type": "number", "description": "Minimal kamera megapikseli"},
            "min_ram_gb": {"type": "number", "description": "Minimal RAM (GB)"},
        },
    },
}

SYSTEM_PROMPT = (
    "Sen telefon do'koni uchun yordamchi AI-agentsan. Foydalanuvchi o'zbek yoki rus tilida "
    "telefon haqida so'rov beradi (narx, kamera, brend va h.k.). Har doim avval "
    "search_phones tool'ini chaqirib bazadan mos telefonlarni top, so'ng natijalarni "
    "qisqa va do'stona tarzda, narxlari bilan birga taklif qil. Agar hech narsa topilmasa, "
    "buni aytib, mezonlarni yumshatishni taklif qil."
)


def _search_phones_sync(min_price=None, max_price=None, brand=None, min_camera_mp=None, min_ram_gb=None):
    """Bloklovchi (sync) DB so'rovi — alohida thread'da chaqiriladi."""
    db = SessionLocal()
    try:
        filters = []
        if min_price is not None:
            filters.append(Phone.price_usd >= min_price)
        if max_price is not None:
            filters.append(Phone.price_usd <= max_price)
        if brand:
            filters.append(Phone.brand.ilike(f"%{brand}%"))
        if min_camera_mp is not None:
            filters.append(Phone.camera_mp >= min_camera_mp)
        if min_ram_gb is not None:
            filters.append(Phone.ram_gb >= min_ram_gb)

        query = db.query(Phone)
        if filters:
            query = query.filter(and_(*filters))
        results = query.limit(8).all()
        return [r.to_text() for r in results]
    finally:
        db.close()


async def search_phones(**params) -> list:
    cached = await get_cached("search_phones", params)
    if cached is not None:
        return cached

    # Sync SQLAlchemy chaqiruvini event loopni bloklamasdan bajaramiz.
    results = await asyncio.to_thread(_search_phones_sync, **params)

    await set_cached("search_phones", params, results)
    return results


async def ask_agent(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[SEARCH_TOOL],
        messages=messages,
    )

    # Agar LLM tool chaqirsa — bazani so'raymiz va natijani qaytaramiz
    iterations = 0
    while response.stop_reason == "tool_use":
        iterations += 1
        if iterations > MAX_TOOL_ITERATIONS:
            return "Kechirasiz, so'rovni qayta ishlab bo'lmadi. Iltimos, savolingizni soddalashtirib qayta yozing."

        tool_use_block = next(b for b in response.content if b.type == "tool_use")
        tool_input = tool_use_block.input
        results = await search_phones(**tool_input)

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": json.dumps(results, ensure_ascii=False) if results else "Hech narsa topilmadi.",
            }],
        })

        response = await client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[SEARCH_TOOL],
            messages=messages,
        )

    text_blocks = [b.text for b in response.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Kechirasiz, javob shakllantirib bo'lmadi."
