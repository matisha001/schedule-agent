"""ORM 映射：赛事信息表（meta 库）。"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TournamentInfoMySQL(Base):
    __tablename__ = "tournament_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    sport: Mapped[str] = mapped_column(String(64))
    season: Mapped[str] = mapped_column(String(64))
    level: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[str] = mapped_column(String(32))
    end_date: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="")
