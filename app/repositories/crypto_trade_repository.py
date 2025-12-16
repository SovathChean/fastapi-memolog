"""Crypto trade repository for data access."""

from decimal import Decimal
from typing import Any

from fastapi import Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.crypto_trade import CryptoTrade, TradeStatus
from app.repositories.base import SQLAlchemyRepository
from config.database import get_db


class CryptoTradeRepository(SQLAlchemyRepository[CryptoTrade]):
    """Repository for CryptoTrade entity database operations."""

    def __init__(self, session: AsyncSession = Depends(get_db)):
        """Initialize repository with database session.

        Args:
            session: Async database session.
        """
        super().__init__(session, CryptoTrade)

    async def find_by_user(
        self,
        user_id: int,
        status: TradeStatus | str | None = None,
        limit: int = 50,
    ) -> list[CryptoTrade]:
        """Get trades for a specific user.

        Args:
            user_id: User ID to filter by.
            status: Optional status filter.
            limit: Maximum results.

        Returns:
            List of trades.
        """
        conditions = [CryptoTrade.user_id == user_id]

        if status is not None:
            if isinstance(status, TradeStatus):
                status = status.value
            conditions.append(CryptoTrade.status == status)

        stmt = (
            select(CryptoTrade)
            .where(and_(*conditions))
            .order_by(CryptoTrade.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_open_trades(self, user_id: int) -> list[CryptoTrade]:
        """Get all open trades for a user.

        Args:
            user_id: User ID to filter by.

        Returns:
            List of open trades.
        """
        return await self.find_by_user(user_id, status=TradeStatus.OPEN)

    async def get_user_summary(self, user_id: int) -> dict[str, Any]:
        """Get P&L summary for a user.

        Args:
            user_id: User ID to summarize.

        Returns:
            Dictionary with summary statistics.
        """
        base_condition = CryptoTrade.user_id == user_id

        # Total trades
        total_stmt = (
            select(func.count())
            .select_from(CryptoTrade)
            .where(base_condition)
        )
        total_result = await self.session.execute(total_stmt)
        total_trades = total_result.scalar() or 0

        # Open trades
        open_stmt = (
            select(func.count())
            .select_from(CryptoTrade)
            .where(and_(base_condition, CryptoTrade.status == TradeStatus.OPEN.value))
        )
        open_result = await self.session.execute(open_stmt)
        open_trades = open_result.scalar() or 0

        # Winning trades
        win_stmt = (
            select(func.count())
            .select_from(CryptoTrade)
            .where(and_(base_condition, CryptoTrade.status == TradeStatus.WIN.value))
        )
        win_result = await self.session.execute(win_stmt)
        winning_trades = win_result.scalar() or 0

        # Losing trades
        loss_stmt = (
            select(func.count())
            .select_from(CryptoTrade)
            .where(and_(base_condition, CryptoTrade.status == TradeStatus.LOSS.value))
        )
        loss_result = await self.session.execute(loss_stmt)
        losing_trades = loss_result.scalar() or 0

        # Total profit
        profit_stmt = (
            select(func.coalesce(func.sum(CryptoTrade.profit), 0))
            .select_from(CryptoTrade)
            .where(base_condition)
        )
        profit_result = await self.session.execute(profit_stmt)
        total_profit = Decimal(str(profit_result.scalar() or 0))

        # Total loss
        loss_sum_stmt = (
            select(func.coalesce(func.sum(CryptoTrade.loss), 0))
            .select_from(CryptoTrade)
            .where(base_condition)
        )
        loss_sum_result = await self.session.execute(loss_sum_stmt)
        total_loss = Decimal(str(loss_sum_result.scalar() or 0))

        # Calculate win rate
        closed_trades = winning_trades + losing_trades
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0

        return {
            "total_trades": total_trades,
            "open_trades": open_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_pnl": total_profit - total_loss,
            "win_rate": round(win_rate, 2),
        }

    async def find_by_coin(
        self,
        user_id: int,
        coin: str,
        limit: int = 20,
    ) -> list[CryptoTrade]:
        """Get trades for a specific coin.

        Args:
            user_id: User ID to filter by.
            coin: Coin/pair to filter by.
            limit: Maximum results.

        Returns:
            List of trades for the coin.
        """
        stmt = (
            select(CryptoTrade)
            .where(
                and_(
                    CryptoTrade.user_id == user_id,
                    CryptoTrade.coin == coin.upper(),
                )
            )
            .order_by(CryptoTrade.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
