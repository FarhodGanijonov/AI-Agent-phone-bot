"""
Bazani namuna telefonlar bilan to'ldirish uchun skript.
Ishga tushirish: python -m app.seed
"""
from app.db import SessionLocal, Phone

SAMPLE_PHONES = [
    dict(brand="Samsung", model="Galaxy A14", price_usd=140, ram_gb=4, storage_gb=128,
         camera_mp=50, battery_mah=5000, description="Arzon, uzoq batareya, kundalik foydalanish uchun yaxshi."),
    dict(brand="Samsung", model="Galaxy S23", price_usd=650, ram_gb=8, storage_gb=256,
         camera_mp=50, battery_mah=3900, description="Flagman, kuchli kamera va protsessor."),
    dict(brand="Xiaomi", model="Redmi Note 13", price_usd=180, ram_gb=8, storage_gb=128,
         camera_mp=108, battery_mah=5000, description="Yuqori megapikselli kamera, narxi mos."),
    dict(brand="Xiaomi", model="Poco X6", price_usd=260, ram_gb=8, storage_gb=256,
         camera_mp=64, battery_mah=5100, description="O'yinlar uchun yaxshi protsessor."),
    dict(brand="Apple", model="iPhone 13", price_usd=520, ram_gb=4, storage_gb=128,
         camera_mp=12, battery_mah=3227, description="iOS, mustahkam, yaxshi kamera sifati."),
    dict(brand="Apple", model="iPhone 15 Pro", price_usd=1050, ram_gb=8, storage_gb=256,
         camera_mp=48, battery_mah=3274, description="Eng yangi flagman, titanium korpus."),
    dict(brand="Infinix", model="Note 30", price_usd=160, ram_gb=8, storage_gb=128,
         camera_mp=108, battery_mah=5000, description="Tez zaryadlash, narxi arzon."),
    dict(brand="Tecno", model="Spark 10", price_usd=110, ram_gb=4, storage_gb=64,
         camera_mp=50, battery_mah=5000, description="Eng arzon variant, kunlik ishlatish uchun."),
]


def seed():
    db = SessionLocal()
    try:
        if db.query(Phone).count() == 0:
            db.bulk_insert_mappings(Phone, SAMPLE_PHONES)
            db.commit()
            print(f"{len(SAMPLE_PHONES)} ta telefon qo'shildi.")
        else:
            print("Baza allaqachon to'ldirilgan.")
    finally:
        db.close()


if __name__ == "__main__":
    from app.db import init_db
    init_db()
    seed()
