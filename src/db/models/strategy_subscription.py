from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class StrategySubscription(Base):
    __tablename__ = "strategy_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    strategy_template_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_templates.id", ondelete="CASCADE"),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )