"""
Redis asosida oddiy async cache.
Maqsad: bir xil filtrlar bilan qilingan search_phones so'rovlari
har safar bazaga bormasin — bu DB yukini va javob vaqtini kamaytiradi.
"""
import hashlib
import json
import logging
from typing import Optional

import redis.asyncio as redis

from app.config import REDIS_URL

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None

CACHE_TTL_SECONDS = 300  # 5 daqiqa: telefon narxlari tez-tez o'zgarmaydi


def _get_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _make_key(prefix: str, params: dict) -> str:
    # Filtr parametrlarini barqaror (tartiblangan) tarzda hash qilamiz,
    # shunda {"max_price": 200, "brand": "samsung"} va
    # {"brand": "samsung", "max_price": 200} bir xil keshga tushadi.
    raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{prefix}:{digest}"


async def get_cached(prefix: str, params: dict):
    try:
        client = _get_client()
        key = _make_key(prefix, params)
        value = await client.get(key)
        return json.loads(value) if value is not None else None
    except Exception:
        # Redis vaqtincha ishlamasa ham bot ishlashda davom etishi kerak —
        # keshni faqat optimallashtirish sifatida ko'ramiz, kritik bog'liqlik emas.
        logger.warning("Redis cache o'qishda xatolik, keshsiz davom etamiz", exc_info=True)
        return None


async def set_cached(prefix: str, params: dict, value) -> None:
    try:
        client = _get_client()
        key = _make_key(prefix, params)
        await client.set(key, json.dumps(value, ensure_ascii=False), ex=CACHE_TTL_SECONDS)
    except Exception:
        logger.warning("Redis cache yozishda xatolik, e'tiborsiz qoldiramiz", exc_info=True)
