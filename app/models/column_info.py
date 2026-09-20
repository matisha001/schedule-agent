"""ORM 映射：字段元数据表（meta 库）。"""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ColumnInfoMySQL(Base):
    __tablename__ = "column_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(32))
    examples: Mapped[list] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text)
    alias: Mapped[list] = mapped_column(JSON)
    table_id: Mapped[str] = mapped_column(String(64), index=True)
