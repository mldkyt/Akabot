from discord import Bot, Cog
from discord.ext.tasks import loop

from utils.temporary_actions import get_tasks_to_run, handle_task, mark_task_handled
from logger import akabot_logger


class TemporaryActions(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        if not self.handle_temporary_actions.is_running():
            self.handle_temporary_actions.start()

    @loop(seconds=60)
    async def handle_temporary_actions(self):
        tasks_to_run = await get_tasks_to_run()

        for task in tasks_to_run:
            action, gid, uid, arg = task

            try:
                await handle_task(self.bot, action, gid, uid, arg)
                await mark_task_handled(gid, uid)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle temporary action {action} for gid {gid} and uid {uid}: {e}")



def setup(bot: Bot):
    bot.add_cog(TemporaryActions(bot))
