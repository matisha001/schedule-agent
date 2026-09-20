"""ORM 映射：比赛/赛程事实表（dw 库）。"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MatchInfoMySQL(Base):
    __tablename__ = "match_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tournament_id: Mapped[str] = mapped_column(String(64), index=True)
    round_name: Mapped[str] = mapped_column(String(64))
    home_team_id: Mapped[str] = mapped_column(String(64), index=True)
    away_team_id: Mapped[str] = mapped_column(String(64), index=True)
    match_time: Mapped[str] = mapped_column(String(32), index=True)
    venue: Mapped[str] = mapped_column(String(255))
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
