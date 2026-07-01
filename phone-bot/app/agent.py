import asyncio
import json
import httpx
from sqlalchemy import and_

from app.config import GEMINI_API_KEY, GEMINI_URL
from app.db import SessionLocal, Phone
from app.cache import get_cached, set_cached

SYSTEM_PROMPT = (
    "Sen telefon do'koni uchun yordamchi AI-agentsan. Foydalanuvchi o'zbek yoki rus tilida "
    "telefon haqida so'rov beradi (narx, kamera, brend va h.k.). Har doim avval "
    "search_phones funksiyasini chaqirib bazadan mos telefonlarni top, so'ng natijalarni "
    "qisqa va do'stona tarzda, narxlari bilan birga taklif qil. Agar hech narsa topilmasa, "
    "buni aytib, mezonlarni yumshatishni taklif qil."
)

TOOLS = [{
    "function_declarations": [{
        "name": "search_phones",
        "description": "Bazadan telefonlarni narx, RAM yoki brend bo'yicha filtrlab qidiradi.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "min_price": {"type": "NUMBER", "description": "Minimal narx (USD)"},
                "max_price": {"type": "NUMBER", "description": "Maksimal narx (USD)"},
                "brand": {"type": "STRING", "description": "Brend nomi"},
                "min_camera_mp": {"type": "NUMBER", "description": "Minimal kamera MP"},
                "min_ram_gb": {"type": "NUMBER", "description": "Minimal RAM (GB)"},
            },
        },
    }]
}]

MAX_TOOL_ITERATIONS = 5


def _search_phones_sync(min_price=None, max_price=None, brand=None, min_camera_mp=None, min_ram_gb=None):
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
        return [r.to_text() for r in query.limit(8).all()]
    finally:
        db.close()


async def search_phones(**params) -> list:
    cached = await get_cached("search_phones", params)
    if cached is not None:
        return cached
    results = await asyncio.to_thread(_search_phones_sync, **params)
    await set_cached("search_phones", params, results)
    return results


async def ask_agent(user_message: str) -> str:
    contents = [
        {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
        {"role": "model", "parts": [{"text": "Tushunarli, yordam beraman!"}]},
        {"role": "user", "parts": [{"text": user_message}]},
    ]

    payload = {
        "contents": contents,
        "tools": TOOLS,
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        iterations = 0
        while iterations < MAX_TOOL_ITERATIONS:
            iterations += 1

            response = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json=payload,
            )
            data = response.json()

            candidate = data["candidates"][0]["content"]
            contents.append(candidate)
            payload["contents"] = contents

            # Tool chaqiruvini tekshirish
            tool_call = None
            for part in candidate.get("parts", []):
                if "functionCall" in part:
                    tool_call = part["functionCall"]
                    break

            if tool_call is None:
                # Yakuniy javob
                text = "".join(
                    p.get("text", "") for p in candidate.get("parts", [])
                )
                return text if text.strip() else "Kechirasiz, javob shakllantirib bo'lmadi."

            # Tool natijasini olish va qaytarish
            params = tool_call.get("args", {})
            results = await search_phones(**params)

            contents.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": tool_call["name"],
                        "response": {
                            "result": results if results else ["Hech narsa topilmadi."]
                        },
                    }
                }],
            })
            payload["contents"] = contents

    return "Kechirasiz, so'rovni qayta ishlab bo'lmadi."
