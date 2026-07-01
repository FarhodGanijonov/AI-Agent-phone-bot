import asyncio
import google.generativeai as genai
from sqlalchemy import and_

from app.config import GEMINI_API_KEY
from app.db import SessionLocal, Phone
from app.cache import get_cached, set_cached

genai.configure(api_key=GEMINI_API_KEY)
MODEL = "gemini-1.5-flash"
MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = (
    "Sen telefon do'koni uchun yordamchi AI-agentsan. Foydalanuvchi o'zbek yoki rus tilida "
    "telefon haqida so'rov beradi (narx, kamera, brend va h.k.). Har doim avval "
    "search_phones funksiyasini chaqirib bazadan mos telefonlarni top, so'ng natijalarni "
    "qisqa va do'stona tarzda, narxlari bilan birga taklif qil. Agar hech narsa topilmasa, "
    "buni aytib, mezonlarni yumshatishni taklif qil."
)

SEARCH_TOOL_GEMINI = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="search_phones",
            description="Bazadan telefonlarni narx, RAM, xotira yoki brend bo'yicha filtrlab qidiradi.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "min_price": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Minimal narx (USD)"),
                    "max_price": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Maksimal narx (USD)"),
                    "brand": genai.protos.Schema(type=genai.protos.Type.STRING, description="Brend nomi, masalan Samsung, Xiaomi, Apple"),
                    "min_camera_mp": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Minimal kamera megapikseli"),
                    "min_ram_gb": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Minimal RAM (GB)"),
                },
            ),
        )
    ]
)


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
        results = query.limit(8).all()
        return [r.to_text() for r in results]
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
    model = genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=SYSTEM_PROMPT,
        tools=[SEARCH_TOOL_GEMINI],
    )

    chat = model.start_chat(history=[])
    response = await asyncio.to_thread(chat.send_message, user_message)

    iterations = 0
    while True:
        iterations += 1
        if iterations > MAX_TOOL_ITERATIONS:
            return "Kechirasiz, so'rovni qayta ishlab bo'lmadi. Iltimos, savolingizni soddalashtirib qayta yozing."

        tool_call = None
        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                tool_call = part.function_call
                break

        if tool_call is None:
            break

        params = dict(tool_call.args)
        results = await search_phones(**params)

        tool_response = genai.protos.Part(
            function_response=genai.protos.FunctionResponse(
                name=tool_call.name,
                response={"result": results if results else ["Hech narsa topilmadi."]},
            )
        )
        response = await asyncio.to_thread(chat.send_message, tool_response)

    text = "".join(part.text for part in response.parts if hasattr(part, "text"))
    return text if text else "Kechirasiz, javob shakllantirib bo'lmadi."