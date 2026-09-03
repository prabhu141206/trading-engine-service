from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class StrategyRequirement(Base):
    __tablename__ = "strategy_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    strategy_template_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_templates.id", ondelete="CASCADE"),
        nullable=False,
    )

    requirement_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )