"""ORM 映射：tournament（schedule_dw 库，V3 定稿）。"""

from sqlalchemy import DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TournamentInfoMySQL(Base):
    __tablename__ = "tournament"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    created_by: Mapped[int] = mapped_column(Integer, index=True)
    game: Mapped[str | None] = mapped_column(String(64), nullable=True)
    game_maps: Mapped[str | None] = mapped_column(String(2000), nullable=True)  # 自由文本
    team_mode: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1团队赛 2个人赛
    start_time: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    reg_start_time: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    reg_end_time: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    max_team_members: Mapped[int] = mapped_column(Integer, default=5)
    max_teams: Mapped[int] = mapped_column(Integer, default=16)
    regist_method: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1办赛者代报名 2选手自主报名
    contact_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 自由文本
    rule_info: Mapped[str | None] = mapped_column(String(2000), nullable=True)  # 自由文本
    status: Mapped[int] = mapped_column(SmallInteger, default=0, index=True)  # 0草稿 1已发布 2报名中 3比赛中 4已结束
    created_at: Mapped[str] = mapped_column(DateTime, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[str] = mapped_column(
        DateTime, server_default="CURRENT_TIMESTAMP", onupdate=func.now()
    )
