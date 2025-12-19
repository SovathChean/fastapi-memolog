"""Handler for task management commands (/add, /done, /pending)."""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from app.models.schemas.task import (
    TaskPeriodType,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskStatusUpdate,
)
from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService
from app.support.task_support import TaskSupport
from app.support.telegram_support import TelegramSupport
from app.telegram_bot.handlers.base import BaseHandler
from config.database import get_session_factory


class TaskHandler(BaseHandler):
    """Handler for task management commands."""

    def __init__(self) -> None:
        """Initialize the handler."""
        super().__init__()
        self.telegram_support = TelegramSupport()

    @property
    def commands(self) -> list[str]:
        """Commands this handler responds to."""
        return ["add", "done", "pending"]

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle task management commands.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        command = self.get_command_name(update)
        args = self.get_command_args(update)

        if command == "add":
            await self._handle_add(update, args)
        elif command == "done":
            await self._handle_done(update, args)
        elif command == "pending":
            await self._handle_pending(update, args)

    async def handle_add_natural(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle natural language add command.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        if not update.message or not update.message.text:
            return

        text = update.message.text
        text_lower = text.lower()

        # Extract title from natural text
        title = None
        for prefix in ["add task:", "create task:", "add:", "create:", "new task:"]:
            if prefix in text_lower:
                title = text[text_lower.find(prefix) + len(prefix) :].strip()
                break

        if not title:
            for word in ["add", "create"]:
                if word in text_lower:
                    idx = text_lower.find(word) + len(word)
                    title = text[idx:].strip()
                    break

        if title:
            await self._handle_add(update, title)
        else:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "I couldn't understand the task. Try: /add [title]"
                ),
            )

    async def handle_add_bulk(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle bulk/complex multi-line task input.

        Uses OpenAI to parse hierarchical task structures like:
        Add Weekly task:
        - work:
          - Task 1
          - Task 2
        - personal:
          - Task 3

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        if not update.message or not update.message.text:
            return

        text = update.message.text

        # Show typing indicator while processing
        await self.send_typing(update)

        # Parse bulk input using OpenAI
        from app.support.bulk_task_parser import get_bulk_task_parser

        bulk_parser = get_bulk_task_parser()

        try:
            parsed = await bulk_parser.parse_bulk_input(text)

            if not parsed.tasks:
                await self.send_message(
                    update,
                    self.telegram_support.format_error(
                        "I couldn't extract any tasks from your message.\n"
                        "Try a format like:\n"
                        "Add weekly tasks:\n"
                        "- Work:\n"
                        "  - Task 1\n"
                        "  - Task 2\n"
                        "- Personal:\n"
                        "  - Task 3"
                    ),
                )
                return

            session_factory = get_session_factory()
            async with session_factory() as session:
                # Get or create user
                user = await self.get_or_create_user(update, session)

                repository = TaskRepository(session)
                task_support = TaskSupport()
                service = TaskService(
                    repository=repository,
                    task_support=task_support,
                )

                today = date.today()
                created_tasks = []

                # Create tasks grouped by category
                for category, title, priority in parsed.tasks:
                    # Parse task details to extract scheduling info
                    parsed_details = self.telegram_support.parse_task_details(title)

                    # Use parsed title (with scheduling keywords removed)
                    # Fall back to original title if parsing resulted in empty
                    final_title = (
                        parsed_details.title if parsed_details.title else title
                    )

                    # If bulk parser detected a non-normal priority, use it
                    # Otherwise, use the priority from parsed_details
                    final_priority = (
                        priority
                        if priority != TaskPriority.NORMAL
                        else parsed_details.priority
                    )

                    tasks = await service.create_multiple_tasks(
                        user_id=user.id,
                        titles=[final_title],
                        category=category,
                        period_type=parsed.period,
                        period_date=today,
                        priorities=[final_priority],
                        durations=[parsed_details.duration_minutes],
                        scheduled_times=[parsed_details.scheduled_time],
                        scheduled_end_times=[parsed_details.scheduled_end_time],
                        scheduled_dates=[parsed_details.scheduled_date],
                        end_dates=[parsed_details.end_date],
                    )
                    created_tasks.extend(tasks)

                # Commit the transaction
                await session.commit()

                # Get period stats
                stats = await service.get_period_stats_quick(
                    user.id, parsed.period, today
                )

                # Format response grouped by category
                response = self._format_bulk_response(
                    tasks=parsed.tasks,
                    period_type=parsed.period.value,
                    total_in_period=stats["total"],
                    completed_in_period=stats["completed"],
                )

                await self.send_message(update, response)

        except Exception as e:
            self.logger.error(f"Failed to parse bulk tasks: {e}")
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Sorry, I couldn't process your tasks. Please try again."
                ),
            )

    def _format_bulk_response(
        self,
        tasks: list[tuple[str, str, TaskPriority]],
        period_type: str,
        total_in_period: int,
        completed_in_period: int,
    ) -> str:
        """Format response for bulk task creation.

        Args:
            tasks: List of (category, title, priority) tuples.
            period_type: Period type string.
            total_in_period: Total tasks in period.
            completed_in_period: Completed tasks in period.

        Returns:
            Formatted response string.
        """
        if not tasks:
            return "No tasks created."

        count = len(tasks)
        plural = "s" if count > 1 else ""
        lines = [f"Created {count} {period_type} task{plural}:", ""]

        # Group by category
        categories: dict[str, list[tuple[str, TaskPriority]]] = {}
        for category, title, priority in tasks:
            if category not in categories:
                categories[category] = []
            categories[category].append((title, priority))

        # Format by category
        task_number = 0
        for category, category_tasks in categories.items():
            lines.append(f"{category}:")
            for title, priority in category_tasks:
                task_number += 1
                priority_icon = ""
                if priority == TaskPriority.HIGH:
                    priority_icon = " "
                elif priority == TaskPriority.LOW:
                    priority_icon = " "
                lines.append(f"  {task_number}. {title}{priority_icon}")
            lines.append("")

        pending = total_in_period - completed_in_period
        period_label = {
            "daily": "Today",
            "weekly": "This week",
            "monthly": "This month",
        }.get(period_type, period_type.title())

        stats = f"{pending} pending, {completed_in_period} completed"
        lines.append(f"{period_label}: {stats}")

        return "\n".join(lines)

    async def handle_complete_natural(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle natural language task completion.

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        import re

        if not update.message or not update.message.text:
            return

        text = update.message.text

        # Extract task number from natural text
        # Patterns: "complete task 3", "done with 5", "finish #2", "mark 1 as done"
        patterns = [
            r"(?:complete|done|finish|mark)\s+(?:task\s+)?#?(\d+)",
            r"#(\d+)\s+(?:is\s+)?(?:done|complete|finished)",
            r"task\s+#?(\d+)\s+(?:is\s+)?(?:done|complete|finished)",
        ]

        task_number = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                task_number = int(match.group(1))
                break

        if task_number:
            await self._handle_done(update, str(task_number))
        else:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "I couldn't understand which task to complete.\n"
                    'Try: /done [number] or "complete task 3"'
                ),
            )

    async def handle_status_update_natural(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle natural language status update with period prefix.

        Handles messages like:
        - "Done daily:\n1. note\n2. note"
        - "Pending weekly:\n1. reason\n2."

        Args:
            update: Telegram update object.
            context: Callback context.
        """
        if not update.message or not update.message.text:
            return

        text = update.message.text

        # Extract action, period, and remaining text
        from app.support.intent_support import IntentSupport

        intent_support = IntentSupport()
        result = intent_support.extract_status_update(text)

        if not result:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Could not parse status update. Use format:\n"
                    "Done weekly:\n"
                    "1. note for task 1\n"
                    "2. note for task 2"
                ),
            )
            return

        action, period, remaining = result

        # If remaining text is empty or just whitespace, show error
        if not remaining.strip():
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    f"Please provide task numbers. Example:\n"
                    f"{action.title()} {period}:\n"
                    "1. note for task\n"
                    "2. another note"
                ),
            )
            return

        # Reformat to match _parse_bulk_task_entries expected format:
        # "weekly:\n1. note\n2. note"
        reformatted_args = f"{period}:\n{remaining}"

        # Delegate to existing handlers
        if action == "done":
            await self._handle_done(update, reformatted_args)
        else:  # action == "pending"
            await self._handle_pending(update, reformatted_args)

    async def _handle_add(self, update: Update, args: str) -> None:
        """Handle /add command with support for multiple tasks, scheduling, priority.

        Supports formats:
        - /add Work task1, task2, task3
        - /add weekly Work task1, task2
        - /add monthly Personal task1
        - /add task1, task2 (defaults to daily, General)
        - /add Work meeting high at 2pm 1h
        - /add task1 at 8pm to 12am, task2 low 30m

        Args:
            update: Telegram update object.
            args: Command arguments.
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide task(s). Usage:\n"
                    "/add Work task1, task2, task3\n"
                    "/add task high at 2pm 1h\n"
                    "/add weekly Personal task1, task2"
                ),
            )
            return

        # Parse the command arguments (period, category, raw task texts)
        period_type, category, raw_titles = self.telegram_support.parse_add_command(
            args
        )

        if not raw_titles:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "No tasks found. Usage:\n"
                    "/add Work task1, task2, task3\n"
                    "/add task high at 2pm 1h\n"
                    "/add weekly Personal task1, task2"
                ),
            )
            return

        # Parse scheduling details from each task text
        parsed_tasks = [
            self.telegram_support.parse_task_details(raw_title)
            for raw_title in raw_titles
        ]

        # Extract parallel lists for service call
        titles = [pt.title for pt in parsed_tasks if pt.title]
        priorities = [pt.priority for pt in parsed_tasks]
        durations = [pt.duration_minutes for pt in parsed_tasks]
        scheduled_times = [pt.scheduled_time for pt in parsed_tasks]
        scheduled_end_times = [pt.scheduled_end_time for pt in parsed_tasks]
        scheduled_dates = [pt.scheduled_date for pt in parsed_tasks]
        end_dates = [pt.end_date for pt in parsed_tasks]

        if not titles:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "No valid task titles found after parsing."
                ),
            )
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            # Get or create user
            user = await self.get_or_create_user(update, session)

            repository = TaskRepository(session)
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                task_support=task_support,
            )

            today = date.today()

            # Create multiple tasks with user_id and scheduling
            tasks = await service.create_multiple_tasks(
                user_id=user.id,
                titles=titles,
                category=category,
                period_type=period_type,
                period_date=today,
                priorities=priorities,
                durations=durations,
                scheduled_times=scheduled_times,
                scheduled_end_times=scheduled_end_times,
                scheduled_dates=scheduled_dates,
                end_dates=end_dates,
            )

            # Get period stats for this user
            stats = await service.get_period_stats_quick(user.id, period_type, today)

            # Convert tasks to response format
            task_responses = [TaskResponse.model_validate(task) for task in tasks]

            # Format and send response
            # Get period type string
            period_str = (
                period_type.value
                if isinstance(period_type, TaskPeriodType)
                else period_type
            )

            # Commit the transaction to persist tasks
            await session.commit()

            response = self.telegram_support.format_bulk_creation_response(
                tasks=task_responses,
                period_type=period_str,
                category=category,
                total_in_period=stats["total"],
                completed_in_period=stats["completed"],
            )

            await self.send_message(update, response)

    # Period type aliases (shorthand support) - class level constant
    PERIOD_ALIASES = {
        "daily": TaskPeriodType.DAILY,
        "day": TaskPeriodType.DAILY,
        "weekly": TaskPeriodType.WEEKLY,
        "week": TaskPeriodType.WEEKLY,
        "monthly": TaskPeriodType.MONTHLY,
        "month": TaskPeriodType.MONTHLY,
    }

    def _parse_bulk_task_entries(
        self,
        args: str,
    ) -> tuple[TaskPeriodType, list[tuple[int, str | None]]]:
        """Parse bulk task entries from command args.

        Supports two formats:
        1. Multi-line (like /add bulk):
           weekly:
           1. reason for task 1
           2. reason for task 2

        2. Inline (comma-separated):
           weekly 1 note1, 2 note2, 3

        Args:
            args: Command arguments.

        Returns:
            Tuple of (period_type, list of (task_number, note_or_reason)).
        """
        import re

        lines = args.strip().split("\n")
        period_type = TaskPeriodType.DAILY
        parsed: list[tuple[int, str | None]] = []

        # Check if first line ends with colon (multi-line format)
        first_line = lines[0].strip()
        is_multiline = first_line.endswith(":") or (
            len(lines) > 1 and re.match(r"^\s*\d+", lines[1])
        )

        if is_multiline:
            # Multi-line format: "weekly:\n1. reason\n2. reason"
            # Extract period from first line (remove colon)
            period_str = first_line.rstrip(":").strip().lower()
            if period_str in self.PERIOD_ALIASES:
                period_type = self.PERIOD_ALIASES[period_str]

            # Parse numbered lines: "1. reason" or "1 reason" or just "1"
            # Skip category headers (lines like "Personal:", "Work:")
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue

                # Skip category headers (word followed by colon, no number)
                if re.match(r"^[A-Za-z]+\s*:$", line):
                    continue

                # Match patterns: "1. reason", "1 reason", "1.", "1"
                match = re.match(r"^\s*(\d+)\.?\s*(.*)$", line)
                if match:
                    task_num = int(match.group(1))
                    note = match.group(2).strip() or None
                    if task_num > 0:
                        parsed.append((task_num, note))
        else:
            # Inline format: "weekly 1 note, 2 note" or "1, 2, 3"
            parts = first_line.split()
            rest_start_idx = 0

            # Check for period type in first word
            if parts and parts[0].lower() in self.PERIOD_ALIASES:
                period_type = self.PERIOD_ALIASES[parts[0].lower()]
                rest_start_idx = 1

            # Join remaining parts and split by comma
            rest = " ".join(parts[rest_start_idx:])
            entries = [e.strip() for e in rest.split(",") if e.strip()]

            # Parse each entry: first token is number, rest is note
            for entry in entries:
                entry_parts = entry.split(None, 1)  # Split into max 2 parts
                if entry_parts:
                    try:
                        task_num = int(entry_parts[0])
                        note = entry_parts[1] if len(entry_parts) > 1 else None
                        if task_num > 0:
                            parsed.append((task_num, note))
                    except ValueError:
                        continue  # Skip invalid entries

        return period_type, parsed

    async def _handle_done(self, update: Update, args: str) -> None:
        """Handle /done command using period-based task number.

        Supports formats:
        - /done 1                      (daily task #1)
        - /done 1 note here            (daily task #1 with note)
        - /done weekly 1               (weekly task #1)
        - /done weekly 1, 2, 3         (multiple tasks)
        - /done weekly 1 note, 2 note  (multiple with notes)
        - Multi-line format:
          weekly:
          1. note for task 1
          2. note for task 2

        Args:
            update: Telegram update object.
            args: Optional period, task number(s), and optional completion note(s).
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide task number(s).\n"
                    "Usage: /done [number] [note]\n"
                    "       /done weekly 1, 2, 3\n"
                    "       /done weekly 1 note, 2 note\n"
                    "Or multi-line:\n"
                    "weekly:\n"
                    "1. note for task 1\n"
                    "2. note for task 2"
                ),
            )
            return

        # Parse bulk task entries
        period_type, task_entries = self._parse_bulk_task_entries(args)

        if not task_entries:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "No valid task numbers found. Please provide at least one number."
                ),
            )
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            # Get or create user
            user = await self.get_or_create_user(update, session)

            repository = TaskRepository(session)
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                task_support=task_support,
            )

            today = date.today()

            # Process each task
            completed_tasks: list[tuple[TaskResponse, str | None]] = []
            failed_tasks: list[tuple[int, str]] = []

            for task_number, completion_note in task_entries:
                # Find task by period number for this user
                task = await service.get_task_by_period_number(
                    user_id=user.id,
                    period_number=task_number,
                    period_type=period_type,
                    period_date=today,
                )

                if not task:
                    failed_tasks.append((task_number, "Task not found"))
                    continue

                try:
                    # Mark as completed using actual task ID with optional note
                    status_data = TaskStatusUpdate(
                        status=TaskStatus.COMPLETED,
                        completion_note=completion_note,
                    )
                    updated_task = await service.update_task_status(
                        task.id, status_data
                    )
                    task_response = TaskResponse.model_validate(updated_task)
                    completed_tasks.append((task_response, completion_note))
                except Exception as e:
                    failed_tasks.append((task_number, str(e)))

            # Commit the transaction to persist changes
            await session.commit()

            # Get updated stats for this user
            stats = await service.get_period_stats_quick(user.id, period_type, today)

            # Format response
            response = self.telegram_support.format_bulk_done_response(
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                total_in_period=stats["total"],
                completed_in_period=stats["completed"],
                period_type=period_type.value,
            )

            await self.send_message(update, response)

    async def _handle_pending(self, update: Update, args: str) -> None:
        """Handle /pending command using period-based task number.

        Supports formats:
        - /pending 1 reason                    (daily task #1)
        - /pending weekly 1 reason             (weekly task #1)
        - /pending weekly 1, 2, 3              (multiple tasks)
        - Multi-line format:
          weekly:
          1. reason for task 1
          2. reason for task 2

        Args:
            update: Telegram update object.
            args: Optional period, task number(s), and optional reason(s).
        """
        if not args:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "Please provide task number(s).\n"
                    "Usage: /pending [number] [reason]\n"
                    "       /pending weekly 1, 2, 3\n"
                    "Or multi-line:\n"
                    "weekly:\n"
                    "1. reason for task 1\n"
                    "2. reason for task 2"
                ),
            )
            return

        # Parse bulk task entries (handles both single and multi-line)
        period_type, task_entries = self._parse_bulk_task_entries(args)

        if not task_entries:
            await self.send_message(
                update,
                self.telegram_support.format_error(
                    "No valid task numbers found. Please provide at least one number."
                ),
            )
            return

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await self.get_or_create_user(update, session)

            repository = TaskRepository(session)
            task_support = TaskSupport()
            service = TaskService(
                repository=repository,
                task_support=task_support,
            )

            today = date.today()

            # Process each task
            pending_tasks: list[tuple[TaskResponse, str | None]] = []
            failed_tasks: list[tuple[int, str]] = []

            for task_number, reason in task_entries:
                task = await service.get_task_by_period_number(
                    user_id=user.id,
                    period_number=task_number,
                    period_type=period_type,
                    period_date=today,
                )

                if not task:
                    failed_tasks.append((task_number, "Task not found"))
                    continue

                try:
                    status_data = TaskStatusUpdate(
                        status=TaskStatus.PENDING,
                        pending_reason=reason,
                    )
                    updated_task = await service.update_task_status(
                        task.id, status_data
                    )
                    task_response = TaskResponse.model_validate(updated_task)
                    pending_tasks.append((task_response, reason))
                except Exception as e:
                    failed_tasks.append((task_number, str(e)))

            await session.commit()

            # Format response
            response = self.telegram_support.format_bulk_pending_response(
                pending_tasks=pending_tasks,
                failed_tasks=failed_tasks,
                period_type=period_type.value,
            )

            await self.send_message(update, response)
