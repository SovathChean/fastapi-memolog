"""Trade handler for crypto bot - add, view, close trades."""

import re
from decimal import Decimal, InvalidOperation

from telegram import Update
from telegram.ext import ContextTypes

from app.crypto_bot.handlers.base import BaseCryptoHandler
from app.models.domain.crypto_trade import TradeStatus
from app.models.schemas.crypto_trade import CryptoTradeCreate
from app.repositories.crypto_trade_repository import CryptoTradeRepository
from app.services.crypto_trade_service import CryptoTradeService
from config.database import get_session_factory


class TradeHandler(BaseCryptoHandler):
    """Handler for trade management commands."""

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["add", "trades", "pnl", "open", "close", "delete", "view"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle trade commands."""
        command = self.get_command_name(update)
        args = self.get_command_args(update)

        if command == "add":
            await self._handle_add(update, args)
        elif command == "trades":
            await self._handle_trades(update)
        elif command == "pnl":
            await self._handle_pnl(update)
        elif command == "open":
            await self._handle_open(update)
        elif command == "close":
            await self._handle_close(update, args)
        elif command == "delete":
            await self._handle_delete(update, args)
        elif command == "view":
            await self._handle_view(update, args)

    async def handle_add_natural(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
    ) -> None:
        """Handle natural language trade input."""
        await self._handle_add(update, text)

    async def handle_close_natural(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
    ) -> None:
        """Handle natural language close input."""
        await self._handle_close_natural(update, text)

    def _parse_trade_input(self, text: str) -> dict:
        """Parse trade input from multi-line format.

        Expected format:
        Add:
        coin: WLDUSDT
        Budget: 7$
        Entry: 1.115
        stoploss: 1.101
        Status: Loss
        Loss: 6.87$
        reason: because I underestimate

        Returns:
            Dictionary with parsed trade data.
        """
        result = {
            "coin": None,
            "direction": "long",
            "budget": None,
            "entry": None,
            "stoploss": None,
            "take_profit": None,
            "exit_price": None,
            "leverage": 50,
            "status": "open",
            "profit": None,
            "loss": None,
            "reason": None,
        }

        # Normalize text
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.lower() == "add:":
                continue

            # Parse key: value format
            match = re.match(r"^([^:]+):\s*(.*)$", line, re.IGNORECASE)
            if not match:
                continue

            key = match.group(1).strip().lower()
            value = match.group(2).strip()

            # Remove $ and common symbols from numeric values
            numeric_value = re.sub(r"[$,]", "", value)

            try:
                if key == "coin":
                    result["coin"] = value.upper()
                elif key == "direction":
                    direction_lower = value.lower()
                    if direction_lower in ["short", "s"]:
                        result["direction"] = "short"
                    else:
                        result["direction"] = "long"
                elif key == "budget":
                    result["budget"] = Decimal(numeric_value)
                elif key == "entry":
                    result["entry"] = Decimal(numeric_value)
                elif key in ["stoploss", "sl", "stop"]:
                    result["stoploss"] = Decimal(numeric_value)
                elif key in ["take_profit", "tp", "takeprofit"]:
                    result["take_profit"] = Decimal(numeric_value)
                elif key in ["exit_price", "exit", "exitprice"]:
                    result["exit_price"] = Decimal(numeric_value)
                elif key == "leverage":
                    result["leverage"] = int(numeric_value)
                elif key == "status":
                    status_lower = value.lower()
                    if status_lower in ["win", "won", "profit"]:
                        result["status"] = "win"
                    elif status_lower in ["loss", "lost", "lose"]:
                        result["status"] = "loss"
                    else:
                        result["status"] = "open"
                elif key == "profit":
                    result["profit"] = Decimal(numeric_value)
                elif key == "loss":
                    result["loss"] = Decimal(numeric_value)
                elif key == "reason":
                    result["reason"] = value
            except (InvalidOperation, ValueError):
                continue

        return result

    def _parse_close_input(self, text: str) -> dict:
        """Parse close input from multi-line format.

        Expected format:
        Close 1:
        status: loss
        note: emotion trade
        Loss: 20$
        exit: 41000

        Returns:
            Dictionary with parsed close data.
        """
        result = {
            "trade_id": None,
            "status": None,
            "exit_price": None,
            "profit": None,
            "loss": None,
            "reason": None,
        }

        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check first line for "close [id]:" pattern
            if line.lower().startswith("close"):
                # Extract trade ID from "close 1:" or "close 1"
                import re

                match = re.search(r"close\s*(\d+)", line, re.IGNORECASE)
                if match:
                    result["trade_id"] = int(match.group(1))
                continue

            # Parse key: value format
            match = re.match(r"^([^:]+):\s*(.*)$", line, re.IGNORECASE)
            if not match:
                continue

            key = match.group(1).strip().lower()
            value = match.group(2).strip()

            # Remove $ and common symbols from numeric values
            numeric_value = re.sub(r"[$,]", "", value)

            try:
                if key == "status":
                    status_lower = value.lower()
                    if status_lower in ["win", "won", "profit"]:
                        result["status"] = "win"
                    elif status_lower in ["loss", "lost", "lose"]:
                        result["status"] = "loss"
                elif key in ["exit", "exit_price", "exitprice", "price"]:
                    result["exit_price"] = Decimal(numeric_value)
                elif key == "profit":
                    result["profit"] = Decimal(numeric_value)
                    if not result["status"]:
                        result["status"] = "win"
                elif key == "loss":
                    result["loss"] = Decimal(numeric_value)
                    if not result["status"]:
                        result["status"] = "loss"
                elif key in ["note", "reason"]:
                    result["reason"] = value
            except (InvalidOperation, ValueError):
                continue

        return result

    async def _handle_add(self, update: Update, args: str) -> None:
        """Handle /add command or natural trade input."""
        if not args:
            await self.send_message(
                update,
                "📝 <b>Add Trade</b>\n\n"
                "Paste your trade details:\n"
                "<code>Add:\n"
                "coin: BTCUSDT\n"
                "Budget: 100$\n"
                "Entry: 42000\n"
                "stoploss: 41000\n"
                "Status: open</code>",
            )
            return

        # Parse the trade input
        parsed = self._parse_trade_input(args)

        # Validate required fields
        if not parsed["coin"]:
            await self.send_message(update, "❌ Missing coin (e.g., coin: BTCUSDT)")
            return
        if not parsed["budget"]:
            await self.send_message(update, "❌ Missing budget (e.g., Budget: 100$)")
            return
        if not parsed["entry"]:
            await self.send_message(update, "❌ Missing entry (e.g., Entry: 42000)")
            return
        if not parsed["stoploss"]:
            await self.send_message(update, "❌ Missing stoploss (e.g., SL: 41000)")
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = CryptoTradeRepository(session)
            service = CryptoTradeService(repository)

            # Create trade
            from app.models.schemas.crypto_trade import TradeDirection

            trade_data = CryptoTradeCreate(
                user_id=user.id,
                coin=parsed["coin"],
                direction=TradeDirection(parsed["direction"]),
                budget=parsed["budget"],
                entry=parsed["entry"],
                stoploss=parsed["stoploss"],
                take_profit=parsed["take_profit"],
                exit_price=parsed["exit_price"],
                leverage=parsed["leverage"],
                status=TradeStatus(parsed["status"]),
                profit=parsed["profit"],
                loss=parsed["loss"],
                reason=parsed["reason"],
            )

            trade = await service.create_trade(trade_data)
            await session.commit()

            # Format response
            response = self._format_trade_created(trade)
            await self.send_message(update, response)

    def _format_trade_created(self, trade) -> str:
        """Format trade creation response."""
        status_emoji = {"open": "🔵", "win": "🟢", "loss": "🔴"}.get(
            trade.status, "⚪"
        )
        direction_emoji = "📈" if trade.direction == "long" else "📉"

        lines = [
            "✅ <b>Trade Recorded</b>",
            "",
            f"💰 <b>{trade.coin}</b>",
            f"{direction_emoji} Direction: {trade.direction.upper()}",
            f"📊 Budget: ${float(trade.budget):.2f}",
            f"🎯 Entry: {float(trade.entry):.2f}",
            f"🛑 Stoploss: {float(trade.stoploss):.2f}",
        ]

        if trade.take_profit:
            lines.append(f"🎯 Take Profit: {float(trade.take_profit):.2f}")
        if trade.leverage != 50:
            lines.append(f"⚡ Leverage: {trade.leverage}x")

        lines.append(f"{status_emoji} Status: {trade.status.upper()}")

        if trade.profit:
            lines.append(f"💵 Profit: ${float(trade.profit):.2f}")
        if trade.loss:
            lines.append(f"💸 Loss: ${float(trade.loss):.2f}")
        if trade.reason:
            lines.append(f"📝 Note: {trade.reason}")

        lines.append(f"\n🆔 Trade ID: {trade.id}")

        return "\n".join(lines)

    async def _handle_trades(self, update: Update) -> None:
        """Handle /trades command - list recent trades."""
        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = CryptoTradeRepository(session)
            service = CryptoTradeService(repository)

            trades = await service.get_user_trades(user.id, limit=10)

            if not trades:
                await self.send_message(
                    update,
                    "📭 No trades yet.\n\nUse /add to record your first trade!",
                )
                return

            lines = ["📊 <b>Recent Trades</b>", ""]

            for trade in trades:
                status_emoji = {"open": "🔵", "win": "🟢", "loss": "🔴"}.get(
                    trade.status, "⚪"
                )
                direction_emoji = "📈" if trade.direction == "long" else "📉"
                pnl = ""
                if trade.profit:
                    pnl = f" +${float(trade.profit):.2f}"
                elif trade.loss:
                    pnl = f" -${float(trade.loss):.2f}"

                lines.append(
                    f"{status_emoji}{direction_emoji} <b>{trade.coin}</b> | "
                    f"${float(trade.budget):.2f} @ {float(trade.entry):.2f}{pnl}"
                )

            await self.send_message(update, "\n".join(lines))

    async def _handle_pnl(self, update: Update) -> None:
        """Handle /pnl command - show P&L summary."""
        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = CryptoTradeRepository(session)
            service = CryptoTradeService(repository)

            summary = await service.get_pnl_summary(user.id)

            net_emoji = "🟢" if summary.net_pnl >= 0 else "🔴"

            response = (
                "📈 <b>P&L Summary</b>\n\n"
                f"📊 Total Trades: {summary.total_trades}\n"
                f"🔵 Open: {summary.open_trades}\n"
                f"🟢 Wins: {summary.winning_trades}\n"
                f"🔴 Losses: {summary.losing_trades}\n\n"
                f"💰 Total Profit: ${float(summary.total_profit):.2f}\n"
                f"💸 Total Loss: ${float(summary.total_loss):.2f}\n"
                f"{net_emoji} Net P&L: ${float(summary.net_pnl):.2f}\n\n"
                f"📊 Win Rate: {summary.win_rate:.1f}%"
            )

            await self.send_message(update, response)

    async def _handle_open(self, update: Update) -> None:
        """Handle /open command - list open trades."""
        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = CryptoTradeRepository(session)
            service = CryptoTradeService(repository)

            trades = await service.get_open_trades(user.id)

            if not trades:
                await self.send_message(
                    update, "📭 No open trades.\n\nAll positions are closed!"
                )
                return

            lines = ["🔵 <b>Open Positions</b>", ""]

            for trade in trades:
                direction_emoji = "📈" if trade.direction == "long" else "📉"
                tp_str = ""
                if trade.take_profit:
                    tp_str = f" | 🎯 TP: {float(trade.take_profit):.2f}"
                lines.append(
                    f"#{trade.id} {direction_emoji} <b>{trade.coin}</b>\n"
                    f"   💰 ${float(trade.budget):.2f} @ {float(trade.entry):.2f}\n"
                    f"   🛑 SL: {float(trade.stoploss):.2f}{tp_str}"
                )
                lines.append("")

            await self.send_message(update, "\n".join(lines))

    async def _handle_close(self, update: Update, args: str) -> None:
        """Handle /close [id] [price] [status] command."""
        parts = args.split()

        if len(parts) < 1:
            await self.send_message(
                update,
                "❌ Usage: /close [trade_id] [exit_price] [win/loss]\n"
                "Example: /close 5 43000 win",
            )
            return

        try:
            trade_id = int(parts[0])
        except ValueError:
            await self.send_message(update, "❌ Invalid trade ID")
            return

        exit_price = None
        status = None

        if len(parts) >= 2:
            try:
                exit_price = float(parts[1])
            except ValueError:
                pass

        if len(parts) >= 3:
            status_str = parts[2].lower()
            if status_str in ["win", "won"]:
                status = TradeStatus.WIN
            elif status_str in ["loss", "lose", "lost"]:
                status = TradeStatus.LOSS

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = CryptoTradeRepository(session)
            service = CryptoTradeService(repository)

            trade = await service.get_trade(trade_id)

            if not trade or trade.user_id != user.id:
                await self.send_message(update, "❌ Trade not found")
                return

            if trade.status != TradeStatus.OPEN.value:
                await self.send_message(update, "❌ Trade is already closed")
                return

            # Update trade
            update_data = {}
            if exit_price:
                update_data["exit_price"] = Decimal(str(exit_price))
            if status:
                update_data["status"] = status.value

            if update_data:
                from app.models.schemas.crypto_trade import CryptoTradeUpdate

                updated = await service.update_trade(
                    trade_id, CryptoTradeUpdate(**update_data)
                )
                await session.commit()

                status_emoji = {"win": "🟢", "loss": "🔴"}.get(
                    updated.status, "⚪"
                )
                exit_info = ""
                if updated.exit_price:
                    exit_info = f"\n📍 Exit: {float(updated.exit_price):.2f}"
                await self.send_message(
                    update,
                    f"✅ Trade #{trade_id} closed\n"
                    f"{status_emoji} Status: {updated.status.upper()}{exit_info}",
                )
            else:
                await self.send_message(
                    update, "❌ Please provide exit price and/or status"
                )

    async def _handle_close_natural(self, update: Update, text: str) -> None:
        """Handle natural language close input.

        Format:
        Close 1:
        status: loss
        note: emotion trade
        Loss: 20$
        exit: 41000
        """
        parsed = self._parse_close_input(text)

        if not parsed["trade_id"]:
            await self.send_message(
                update,
                "❌ <b>Close Trade</b>\n\n"
                "Format:\n"
                "<code>Close 1:\n"
                "status: loss\n"
                "note: emotion trade\n"
                "Loss: 20$\n"
                "exit: 41000</code>",
            )
            return

        trade_id = parsed["trade_id"]

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = CryptoTradeRepository(session)
            service = CryptoTradeService(repository)

            trade = await service.get_trade(trade_id)

            if not trade or trade.user_id != user.id:
                await self.send_message(update, "❌ Trade not found")
                return

            if trade.status != TradeStatus.OPEN.value:
                await self.send_message(update, "❌ Trade is already closed")
                return

            # Build update data
            update_data = {}
            if parsed["status"]:
                update_data["status"] = parsed["status"]
            if parsed["exit_price"]:
                update_data["exit_price"] = parsed["exit_price"]
            if parsed["profit"]:
                update_data["profit"] = parsed["profit"]
            if parsed["loss"]:
                update_data["loss"] = parsed["loss"]
            if parsed["reason"]:
                update_data["reason"] = parsed["reason"]

            if not update_data:
                await self.send_message(
                    update, "❌ Please provide status, exit price, or P&L"
                )
                return

            from app.models.schemas.crypto_trade import CryptoTradeUpdate

            updated = await service.update_trade(
                trade_id, CryptoTradeUpdate(**update_data)
            )
            await session.commit()

            # Format response
            status_emoji = {"win": "🟢", "loss": "🔴"}.get(updated.status, "⚪")

            lines = [
                f"✅ <b>Trade #{trade_id} Closed</b>",
                "",
                f"💰 <b>{updated.coin}</b>",
                f"{status_emoji} Status: {updated.status.upper()}",
            ]

            if updated.profit:
                lines.append(f"💵 Profit: ${float(updated.profit):.2f}")
            if updated.loss:
                lines.append(f"💸 Loss: ${float(updated.loss):.2f}")
            if updated.exit_price:
                lines.append(f"📍 Exit: {float(updated.exit_price):.2f}")
            if updated.reason:
                lines.append(f"📝 Note: {updated.reason}")

            await self.send_message(update, "\n".join(lines))

    async def _handle_delete(self, update: Update, args: str) -> None:
        """Handle /delete [id] command."""
        if not args:
            await self.send_message(update, "❌ Usage: /delete [trade_id]")
            return

        try:
            trade_id = int(args.strip())
        except ValueError:
            await self.send_message(update, "❌ Invalid trade ID")
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = CryptoTradeRepository(session)
            service = CryptoTradeService(repository)

            trade = await service.get_trade(trade_id)

            if not trade or trade.user_id != user.id:
                await self.send_message(update, "❌ Trade not found")
                return

            await service.delete_trade(trade_id)
            await session.commit()

            await self.send_message(update, f"🗑️ Trade #{trade_id} deleted")

    async def _handle_view(self, update: Update, args: str) -> None:
        """Handle /view [id] command - view detailed trade info."""
        if not args:
            await self.send_message(update, "❌ Usage: /view [trade_id]")
            return

        try:
            trade_id = int(args.strip())
        except ValueError:
            await self.send_message(update, "❌ Invalid trade ID")
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = CryptoTradeRepository(session)
            service = CryptoTradeService(repository)

            trade = await service.get_trade(trade_id)

            if not trade or trade.user_id != user.id:
                await self.send_message(update, "❌ Trade not found")
                return

            # Format detailed view
            status_emoji = {"open": "🔵", "win": "🟢", "loss": "🔴"}.get(
                trade.status, "⚪"
            )
            direction_emoji = "📈" if trade.direction == "long" else "📉"

            lines = [
                f"💰 <b>{trade.coin}</b>",
                f"{direction_emoji} Direction: {trade.direction.upper()}",
                f"📊 Budget: ${float(trade.budget):.2f}",
                f"🎯 Entry: {float(trade.entry):.2f}",
                f"🛑 Stoploss: {float(trade.stoploss):.2f}",
            ]

            if trade.take_profit:
                lines.append(f"🎯 Take Profit: {float(trade.take_profit):.2f}")

            if trade.leverage != 50:
                lines.append(f"⚡ Leverage: {trade.leverage}x")

            lines.append(f"{status_emoji} Status: {trade.status.upper()}")

            if trade.profit:
                lines.append(f"💵 Profit: ${float(trade.profit):.2f}")
            if trade.loss:
                lines.append(f"💸 Loss: ${float(trade.loss):.2f}")
            if trade.exit_price:
                lines.append(f"📍 Close at: {float(trade.exit_price):.2f}")
            if trade.reason:
                lines.append(f"📝 Note: {trade.reason}")

            lines.append(f"\n🆔 Trade ID: {trade.id}")

            await self.send_message(update, "\n".join(lines))
