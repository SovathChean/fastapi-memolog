"""Crypto trade service for business logic."""

import logging

from app.models.domain.crypto_trade import CryptoTrade, TradeStatus
from app.models.schemas.crypto_trade import (
    CryptoTradeCreate,
    CryptoTradeSummary,
    CryptoTradeUpdate,
)
from app.repositories.crypto_trade_repository import CryptoTradeRepository


class CryptoTradeService:
    """Service for crypto trade operations."""

    def __init__(self, repository: CryptoTradeRepository):
        """Initialize service with repository.

        Args:
            repository: Crypto trade repository.
        """
        self.repository = repository
        self.logger = logging.getLogger(__name__)

    async def create_trade(self, data: CryptoTradeCreate) -> CryptoTrade:
        """Create a new trade.

        Args:
            data: Trade creation data.

        Returns:
            Created trade.
        """
        if isinstance(data.status, TradeStatus):
            status_val = data.status.value
        else:
            status_val = data.status
        trade = CryptoTrade(
            user_id=data.user_id,
            coin=data.coin.upper(),
            direction=data.direction.value,
            budget=data.budget,
            entry=data.entry,
            stoploss=data.stoploss,
            take_profit=data.take_profit,
            exit_price=data.exit_price,
            leverage=data.leverage,
            status=status_val,
            profit=data.profit,
            loss=data.loss,
            reason=data.reason,
        )
        created = await self.repository.insert(trade)
        self.logger.info(f"Created trade: {created.id} for user {data.user_id}")
        return created

    async def get_trade(self, trade_id: int) -> CryptoTrade | None:
        """Get trade by ID.

        Args:
            trade_id: Trade ID.

        Returns:
            Trade if found, None otherwise.
        """
        return await self.repository.selectById(trade_id)

    async def update_trade(
        self,
        trade_id: int,
        data: CryptoTradeUpdate,
    ) -> CryptoTrade | None:
        """Update an existing trade.

        Args:
            trade_id: Trade ID.
            data: Update data.

        Returns:
            Updated trade if found, None otherwise.
        """
        update_data = data.model_dump(exclude_none=True)
        if "status" in update_data and isinstance(update_data["status"], TradeStatus):
            update_data["status"] = update_data["status"].value

        if not update_data:
            return await self.get_trade(trade_id)

        updated = await self.repository.update(trade_id, **update_data)
        if updated:
            self.logger.info(f"Updated trade: {trade_id}")
        return updated

    async def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        status: TradeStatus,
        profit: float | None = None,
        loss: float | None = None,
        reason: str | None = None,
    ) -> CryptoTrade | None:
        """Close a trade with exit details.

        Args:
            trade_id: Trade ID.
            exit_price: Exit price.
            status: Final status (win/loss).
            profit: Profit amount if win.
            loss: Loss amount if loss.
            reason: Optional closing reason.

        Returns:
            Updated trade if found, None otherwise.
        """
        update_data = {
            "exit_price": exit_price,
            "status": status.value,
        }
        if profit is not None:
            update_data["profit"] = profit
        if loss is not None:
            update_data["loss"] = loss
        if reason is not None:
            update_data["reason"] = reason

        updated = await self.repository.update(trade_id, **update_data)
        if updated:
            self.logger.info(f"Closed trade: {trade_id} with status {status.value}")
        return updated

    async def get_user_trades(
        self,
        user_id: int,
        status: TradeStatus | None = None,
        limit: int = 50,
    ) -> list[CryptoTrade]:
        """Get trades for a user.

        Args:
            user_id: User ID.
            status: Optional status filter.
            limit: Maximum results.

        Returns:
            List of trades.
        """
        return await self.repository.find_by_user(user_id, status=status, limit=limit)

    async def get_open_trades(self, user_id: int) -> list[CryptoTrade]:
        """Get all open trades for a user.

        Args:
            user_id: User ID.

        Returns:
            List of open trades.
        """
        return await self.repository.find_open_trades(user_id)

    async def get_pnl_summary(self, user_id: int) -> CryptoTradeSummary:
        """Get P&L summary for a user.

        Args:
            user_id: User ID.

        Returns:
            P&L summary.
        """
        stats = await self.repository.get_user_summary(user_id)
        return CryptoTradeSummary(**stats)

    async def delete_trade(self, trade_id: int) -> bool:
        """Delete a trade.

        Args:
            trade_id: Trade ID.

        Returns:
            True if deleted, False if not found.
        """
        deleted = await self.repository.delete(trade_id)
        if deleted:
            self.logger.info(f"Deleted trade: {trade_id}")
        return deleted
