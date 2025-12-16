"""Crypto trade domain model for P&L tracking."""

from decimal import Decimal
from enum import Enum

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.domain.base import BaseEntity


class TradeStatus(str, Enum):
    """Trade status enumeration."""

    OPEN = "open"
    WIN = "win"
    LOSS = "loss"


class CryptoTrade(BaseEntity):
    """Crypto trade entity for profit/loss tracking."""

    __tablename__ = "crypto_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coin: Mapped[str] = mapped_column(String(50), nullable=False)
    budget: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    entry: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    stoploss: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TradeStatus.OPEN.value,
    )
    profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship to user (many-to-one)
    user: Mapped["TelegramUser"] = relationship(  # noqa: F821
        "TelegramUser",
        back_populates="crypto_trades",
    )
