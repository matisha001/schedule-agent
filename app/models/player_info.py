"""ORM 映射：player（schedule_dw 库，V3 定稿）。"""

from sqlalchemy import DateTime, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlayerInfoMySQL(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # TEMP 指虚拟 user id=1
    nickname: Mapped[str] = mapped_column(String(64))
    is_captain: Mapped[int] = mapped_column(SmallInteger, default=0)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")  # AGREED/PENDING/REJECTED
    player_type: Mapped[str] = mapped_column(String(16), default="TEMP")  # TEMP临时 REAL正式
    created_at: Mapped[str] = mapped_column(DateTime, server_default="CURRENT_TIMESTAMP")
