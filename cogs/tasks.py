import asyncio
import json

import sentry_sdk
from discord import Bot, Cog
from discord.ext.tasks import loop

import utils.reaction_roles  # noqa: F401  registers task handlers
from database import engine
from logger import akabot_logger
from utils.tasks import (
    TASK_HANDLERS,
    delete_task,
    fail_task,
    get_pending_tasks,
    retry_or_fail,
)


class Tasks(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot
        self.running = False

    @Cog.listener()
    async def on_ready(self):
        if not self.process_tasks.is_running():
            self.process_tasks.start()

    @loop(seconds=1)
    async def process_tasks(self):
        if self.running:
            return

        self.running = True
        try:
            with engine.begin() as c:
                rows = get_pending_tasks(c)

            if not rows:
                return

            groups: dict[str, list] = {}
            for row in rows:
                groups.setdefault(row[1], []).append(row)

            await asyncio.gather(
                *(
                    self.run_group(task_type, group)
                    for task_type, group in groups.items()
                )
            )
        finally:
            self.running = False

    async def run_group(self, task_type: str, rows: list) -> None:
        handler = TASK_HANDLERS.get(task_type)

        for row in rows:
            task_id, _, data, attempts, _ = row

            if handler is None:
                with engine.begin() as c:
                    fail_task(c, task_id, f"Unknown task type {task_type}")
                continue

            try:
                await handler(self.bot, json.loads(data))
            except Exception as e:
                akabot_logger.exception(f"Task {task_id} ({task_type}) failed: {e}")
                sentry_sdk.capture_exception(e)
                with engine.begin() as c:
                    retry_or_fail(c, task_id, attempts, str(e))
            else:
                with engine.begin() as c:
                    delete_task(c, task_id)


def setup(bot: Bot):
    bot.add_cog(Tasks(bot))
