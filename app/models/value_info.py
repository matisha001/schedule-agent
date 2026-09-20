"""ORM 映射：取值字典表（meta 库）。"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ValueInfoMySQL(Base):
    __tablename__ = "value_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    field_name: Mapped[str] = mapped_column(String(128), index=True)
    value: Mapped[str] = mapped_column(String(255))
    aliases: Mapped[list] = mapped_column("aliases", String(1024), default="[]")
    description: Mapped[str] = mapped_column(Text)
