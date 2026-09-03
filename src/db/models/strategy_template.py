from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    strategy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )