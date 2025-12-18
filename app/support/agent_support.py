"""Agent support module with LangChain tools for task analysis."""

from datetime import date
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.models.schemas.task import TaskPeriodType, TaskResponse, TaskStatus
from app.services.task_service import TaskService
from app.support.langchain_support import get_langchain_support
from app.support.task_support import TaskSupport

AGENT_SYSTEM_PROMPT = """You are a helpful task management assistant.

You have access to tools to help answer questions about the user's tasks:
- count_tasks: Count pending/completed tasks for a period
- get_priority_tasks: Get tasks ordered by priority (high priority and due soon first)
- get_task_stats: Get completion statistics and progress

When the user asks analytical questions, use the appropriate tool:
- "how many tasks pending?" → Use count_tasks tool
- "what should I do first?" → Use get_priority_tasks tool
- "what's my progress?" or "completion rate" → Use get_task_stats tool
- "show high priority tasks" → Use get_priority_tasks tool

For simple task searches or general questions, you can answer directly.
Keep responses concise and friendly for Telegram display.
Use emojis sparingly for readability.

Today's date is {today}.
"""

# Tool definitions for bind_tools
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "count_tasks",
            "description": (
                "Count tasks for a period. Use when user asks "
                "'how many tasks' or wants to know task counts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": (
                            "Period type - daily (today), weekly "
                            "(this week), or monthly (this month)"
                        ),
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "completed", "all"],
                        "description": (
                            "Filter by status - pending, completed, or all"
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_priority_tasks",
            "description": (
                "Get high priority pending tasks. Use for 'what should I do "
                "first', 'show priority tasks', or prioritization questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "Period type - daily, weekly, or monthly",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tasks to return (default: 5)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_stats",
            "description": (
                "Get task statistics including completion rate. Use for "
                "progress questions, completion rate, or statistics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "Period type - daily, weekly, or monthly",
                    },
                },
                "required": [],
            },
        },
    },
]


class AgentSupport:
    """LangChain agent for intelligent task queries with tools."""

    def __init__(self) -> None:
        """Initialize agent with LangChain chat model and tools."""
        self.langchain = get_langchain_support()
        self.task_support = TaskSupport()

        # Bind tools to the chat model
        self.agent = self.langchain.chat_model.bind_tools(TOOL_DEFINITIONS)

    async def answer_question(
        self,
        user_id: int,
        question: str,
        task_service: TaskService,
        tasks_context: list[TaskResponse] | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Answer question using tools when needed.

        Args:
            user_id: User ID for task queries.
            question: User's question.
            task_service: Task service for database operations.
            tasks_context: Optional pre-fetched relevant tasks.
            history: Optional conversation history.

        Returns:
            AI response string.
        """
        today = date.today()

        # Build system prompt with today's date
        system_prompt = AGENT_SYSTEM_PROMPT.format(today=today.strftime("%Y-%m-%d"))

        # Add task context if available
        if tasks_context:
            context = self._format_tasks_context(tasks_context)
            system_prompt += f"\n\nRelevant tasks from search:\n{context}"

        # Build messages
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        # Add conversation history if available
        if history:
            for msg in history[-5:]:  # Last 5 exchanges
                if msg.get("human"):
                    messages.append(HumanMessage(content=msg["human"]))
                if msg.get("ai"):
                    messages.append(AIMessage(content=msg["ai"]))

        # Add current question
        messages.append(HumanMessage(content=question))

        # First LLM call - may include tool calls
        response = await self.agent.ainvoke(messages)

        # Check if tools were called
        if hasattr(response, "tool_calls") and response.tool_calls:
            # Execute tool calls
            messages.append(response)

            for tool_call in response.tool_calls:
                tool_result = await self._execute_tool(
                    tool_call=tool_call,
                    user_id=user_id,
                    task_service=task_service,
                    period_date=today,
                )
                messages.append(
                    ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call["id"],
                    )
                )

            # Get final response after tool execution
            final_response = await self.agent.ainvoke(messages)
            return final_response.content

        # No tools called, return direct response
        return response.content

    async def _execute_tool(
        self,
        tool_call: dict,
        user_id: int,
        task_service: TaskService,
        period_date: date,
    ) -> str:
        """Execute a tool call and return the result.

        Args:
            tool_call: Tool call from LLM response.
            user_id: User ID for queries.
            task_service: Task service instance.
            period_date: Date for period calculations.

        Returns:
            Tool execution result as string.
        """
        tool_name = tool_call["name"]
        args = tool_call.get("args", {})

        if tool_name == "count_tasks":
            return await self._count_tasks(
                user_id=user_id,
                task_service=task_service,
                period=args.get("period", "daily"),
                status=args.get("status", "all"),
                period_date=period_date,
            )
        elif tool_name == "get_priority_tasks":
            return await self._get_priority_tasks(
                user_id=user_id,
                task_service=task_service,
                period=args.get("period", "daily"),
                limit=args.get("limit", 5),
                period_date=period_date,
            )
        elif tool_name == "get_task_stats":
            return await self._get_task_stats(
                user_id=user_id,
                task_service=task_service,
                period=args.get("period", "daily"),
                period_date=period_date,
            )
        else:
            return f"Unknown tool: {tool_name}"

    async def _count_tasks(
        self,
        user_id: int,
        task_service: TaskService,
        period: str,
        status: str,
        period_date: date,
    ) -> str:
        """Count tasks for a period."""
        period_type = TaskPeriodType(period)

        stats = await task_service.get_period_stats_quick(
            user_id=user_id,
            period_type=period_type,
            period_date=period_date,
        )

        if status == "pending":
            return f"Pending tasks ({period}): {stats['pending']}"
        elif status == "completed":
            return f"Completed tasks ({period}): {stats['completed']}"
        else:
            return (
                f"Task count ({period}): "
                f"{stats['total']} total, "
                f"{stats['pending']} pending, "
                f"{stats['completed']} completed"
            )

    async def _get_priority_tasks(
        self,
        user_id: int,
        task_service: TaskService,
        period: str,
        limit: int,
        period_date: date,
    ) -> str:
        """Get high priority pending tasks."""
        period_type = TaskPeriodType(period)

        tasks = await task_service.get_tasks_by_period(
            user_id=user_id,
            period_type=period_type,
            period_date=period_date,
        )

        # Filter pending tasks and sort by priority
        pending_tasks = [
            t
            for t in tasks
            if t.status == TaskStatus.PENDING.value or t.status == TaskStatus.PENDING
        ]

        # Sort by priority (high > normal > low) and then by scheduled time/end_date
        priority_order = {"high": 0, "normal": 1, "low": 2}

        def sort_key(task):
            priority = task.priority
            if hasattr(priority, "value"):
                priority = priority.value
            p_order = priority_order.get(priority, 1)

            # Tasks with earlier scheduled_time or end_date come first
            time_key = None
            if task.scheduled_time:
                time_key = task.scheduled_time
            elif task.end_date:
                time_key = task.end_date

            return (p_order, time_key or date.max)

        sorted_tasks = sorted(pending_tasks, key=sort_key)[:limit]

        if not sorted_tasks:
            return f"No pending tasks found for {period}."

        result_lines = [f"Priority tasks ({period}):"]
        for i, task in enumerate(sorted_tasks, 1):
            priority = task.priority
            if hasattr(priority, "value"):
                priority = priority.value

            line = f"{i}. [{priority.upper()}] {task.title}"

            if task.scheduled_time:
                line += f" (scheduled: {task.scheduled_time})"
            elif task.end_date:
                line += f" (due: {task.end_date})"

            if task.category:
                line += f" [{task.category}]"

            result_lines.append(line)

        return "\n".join(result_lines)

    async def _get_task_stats(
        self,
        user_id: int,
        task_service: TaskService,
        period: str,
        period_date: date,
    ) -> str:
        """Get task statistics."""
        period_type = TaskPeriodType(period)

        stats = await task_service.get_period_stats_quick(
            user_id=user_id,
            period_type=period_type,
            period_date=period_date,
        )

        total = stats["total"]
        completed = stats["completed"]
        pending = stats["pending"]

        if total == 0:
            return f"No tasks found for {period}."

        completion_rate = (completed / total) * 100

        return (
            f"Task statistics ({period}):\n"
            f"- Total tasks: {total}\n"
            f"- Completed: {completed}\n"
            f"- Pending: {pending}\n"
            f"- Completion rate: {completion_rate:.1f}%"
        )

    def _format_tasks_context(self, tasks: list[TaskResponse]) -> str:
        """Format tasks for context inclusion in prompt."""
        if not tasks:
            return "No tasks found."

        lines = []
        for task in tasks[:5]:  # Limit to 5 tasks for context
            priority = task.priority
            if hasattr(priority, "value"):
                priority = priority.value

            status = task.status
            if hasattr(status, "value"):
                status = status.value

            line = f"- {task.title} [{status}] [{priority}]"
            if task.category:
                line += f" ({task.category})"
            lines.append(line)

        return "\n".join(lines)


@lru_cache
def get_agent_support() -> AgentSupport:
    """Get cached agent support instance."""
    return AgentSupport()
