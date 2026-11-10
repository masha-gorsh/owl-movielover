from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    # формат: "<соль в hex>$<хэш в hex>"
    password_hash: Mapped[str] = mapped_column(String(255))