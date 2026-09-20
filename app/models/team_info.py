"""ORM 映射：team（schedule_dw 库，V3 定稿）。"""

from sqlalchemy import DateTime, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TeamInfoMySQL(Base):
    __tablename__ = "team"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(64))
    status: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0待审核 1已确认 2已驳回 3已取消
    created_at: Mapped[str] = mapped_column(DateTime, server_default="CURRENT_TIMESTAMP")
