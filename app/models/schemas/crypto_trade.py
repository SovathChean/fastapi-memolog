"""Pydantic schemas for crypto trade operations."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class TradeStatus(str, Enum):
    """Trade status enumeration."""

    OPEN = "open"
    WIN = "win"
    LOSS = "loss"


class TradeDirection(str, Enum):
    """Trade direction enumeration."""

    LONG = "long"
    SHORT = "short"


class CryptoTradeCreate(BaseModel):
    """Schema for creating a crypto trade."""

    user_id: int = Field(..., description="User ID")
    coin: str = Field(..., max_length=50, description="Trading pair (e.g., WLDUSDT)")
    direction: TradeDirection = Field(
        default=TradeDirection.LONG, description="Trade direction (long/short)"
    )
    budget: Decimal = Field(..., gt=0, description="Investment amount")
    entry: Decimal = Field(..., gt=0, description="Entry price")
    stoploss: Decimal = Field(..., gt=0, description="Stop loss price")
    take_profit: Decimal | None = Field(None, gt=0, description="Take profit price")
    exit_price: Decimal | None = Field(None, gt=0, description="Actual exit price")
    leverage: int = Field(default=50, ge=1, le=200, description="Leverage multiplier")
    status: TradeStatus = Field(default=TradeStatus.OPEN, description="Trade status")
    profit: Decimal | None = Field(None, description="Profit amount")
    loss: Decimal | None = Field(None, description="Loss amount")
    reason: str | None = Field(None, description="Trade notes/reason")


class CryptoTradeUpdate(BaseModel):
    """Schema for updating a crypto trade."""

    exit_price: Decimal | None = Field(None, gt=0, description="Actual exit price")
    status: TradeStatus | None = Field(None, description="Trade status")
    profit: Decimal | None = Field(None, description="Profit amount")
    loss: Decimal | None = Field(None, description="Loss amount")
    reason: str | None = Field(None, description="Trade notes/reason")


class CryptoTradeResponse(BaseModel):
    """Schema for crypto trade response."""

    id: int
    user_id: int
    coin: str
    direction: str
    budget: Decimal
    entry: Decimal
    stoploss: Decimal
    take_profit: Decimal | None
    exit_price: Decimal | None
    leverage: int
    status: str
    profit: Decimal | None
    loss: Decimal | None
    reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CryptoTradeSummary(BaseModel):
    """Schema for P&L summary."""

    total_trades: int
    open_trades: int
    winning_trades: int
    losing_trades: int
    total_profit: Decimal
    total_loss: Decimal
    net_pnl: Decimal
    win_rate: float
