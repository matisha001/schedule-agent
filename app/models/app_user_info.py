"""ORM 映射：app_user（schedule_dw 库）。"""

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AppUserInfoMySQL(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    nickname: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, server_default="CURRENT_TIMESTAMP")
