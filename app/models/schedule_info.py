"""ORM 映射：schedule（schedule_dw 库，V3 定稿）。"""

from sqlalchemy import DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ScheduleInfoMySQL(Base):
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(Integer, index=True)
    phase_id: Mapped[int] = mapped_column(Integer, index=True)
    round: Mapped[int] = mapped_column(Integer, default=1)
    round_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bo: Mapped[int] = mapped_column(Integer, default=1)  # BO 局数
    is_final: Mapped[int] = mapped_column(SmallInteger, default=0)
    home_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    away_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=0, index=True)  # 0未开赛 1进行中 2已结束 3已取消
    start_time: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[str] = mapped_column(
        DateTime, server_default="CURRENT_TIMESTAMP", onupdate=func.now()
    )
