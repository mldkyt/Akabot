from discord import Bot, Cog
from discord.ext.tasks import loop

from utils.temporary_actions import (
    MAX_ATTEMPTS,
    get_tasks_to_run,
    handle_task,
    mark_task_failed,
    mark_task_handled,
)
from logger import akabot_logger


class TemporaryActions(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.handle_temporary_actions.is_running():
            self.handle_temporary_actions.start()

    @loop(seconds=60)
    async def handle_temporary_actions(self):
        tasks_to_run = await get_tasks_to_run()

        for task_id, action, gid, uid, arg, attempts in tasks_to_run:
            try:
                await handle_task(self.bot, action, gid, uid, arg)
            except Exception:
                akabot_logger.exception(
                    f"Failed to handle temporary action {action} for guild {gid} and user {uid}"
                )
                if attempts + 1 >= MAX_ATTEMPTS:
                    akabot_logger.error(
                        f"Giving up on temporary action {action} for guild {gid} and user {uid} after {MAX_ATTEMPTS} attempts"
                    )
                    await mark_task_handled(task_id)
                else:
                    await mark_task_failed(task_id)
            else:
                await mark_task_handled(task_id)


def setup(bot: Bot):
    bot.add_cog(TemporaryActions(bot))
