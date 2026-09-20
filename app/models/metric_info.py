"""ORM 映射：指标信息表（meta 库）。"""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetricInfoMySQL(Base):
    __tablename__ = "metric_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    agg_type: Mapped[str] = mapped_column(String(32))
    expression: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    alias: Mapped[list] = mapped_column(JSON)
    table_id: Mapped[str] = mapped_column(String(64), index=True)
