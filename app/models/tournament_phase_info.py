"""ORM 映射：tournament_phase（schedule_dw 库，V3 定稿）。"""

from sqlalchemy import DateTime, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TournamentPhaseInfoMySQL(Base):
    __tablename__ = "tournament_phase"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(32))
    start_time: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0未开始 1进行中 2已结束
