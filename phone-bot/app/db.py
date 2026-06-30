from sqlalchemy import create_engine, Column, Integer, String, Numeric, Text, Index
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# pool_size/max_overflow: bir vaqtning o'zida bir nechta foydalanuvchi so'rov
# yuborganda DB connection navbatda qolib ketmasligi uchun.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Phone(Base):
    __tablename__ = "phones"

    id = Column(Integer, primary_key=True)
    brand = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    price_usd = Column(Numeric(10, 2), nullable=False)
    ram_gb = Column(Integer)
    storage_gb = Column(Integer)
    camera_mp = Column(Integer)
    battery_mah = Column(Integer)
    description = Column(Text)

    __table_args__ = (
        # search_phones filtrlarida eng ko'p ishlatiladigan ustunlar uchun index.
        # Index'siz har bir filtr to'liq jadval skanini (full table scan) talab qiladi.
        Index("ix_phones_price_usd", "price_usd"),
        Index("ix_phones_brand", "brand"),
        Index("ix_phones_camera_mp", "camera_mp"),
        Index("ix_phones_ram_gb", "ram_gb"),
    )

    def to_text(self) -> str:
        return (
            f"{self.brand} {self.model} — ${self.price_usd}, "
            f"RAM: {self.ram_gb}GB, Xotira: {self.storage_gb}GB, "
            f"Kamera: {self.camera_mp}MP, Batareya: {self.battery_mah}mAh. "
            f"{self.description or ''}"
        )


def init_db():
    Base.metadata.create_all(bind=engine)
