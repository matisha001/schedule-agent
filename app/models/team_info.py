"""ORM 映射：球队信息表（meta 库）。"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TeamInfoMySQL(Base):
    __tablename__ = "team_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    sport: Mapped[str] = mapped_column(String(64))
    short_name: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(128))
    home_venue: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
