import datetime

from discord import Cog, Bot, slash_command, IntegrationType, ApplicationContext
from discord.ext.tasks import loop

from utils.reminders import schedule_reminder, reminders_going_off, AddAkabotAsUserInstall, mark_reminders_as_read

class Reminders(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.check_reminders.is_running():
            self.check_reminders.start()


    @slash_command(integration_types=[IntegrationType.user_install])
    async def remind(self, ctx: ApplicationContext, what: str, days: int = 0, hours: int = 0, minutes: int = 0):
        timedelta = datetime.timedelta(days=days, hours=hours, minutes=minutes)
        if timedelta.total_seconds() < 0:
            await ctx.respond("The reminder must be sent in the future.", ephemeral=True)
            return

        await schedule_reminder(ctx.user.id, what, timedelta)
        await ctx.respond(
            "Reminder set successfully. Make sure you have Akabot added as a user install for it to send reminders!",
            view=AddAkabotAsUserInstall(self.bot),
            ephemeral=True
        )

    @loop(minutes=1)
    async def check_reminders(self):
        uids = []

        async for uid, content in reminders_going_off():
            uids.append(uid)
            user = self.bot.get_user(uid)
            if user is None:
                continue

            try:
                await user.send(f"Reminder: {content}\n-# Sent by Akabot")
            except Exception:
                continue

        await mark_reminders_as_read(*uids)


def setup(bot: Bot):
    bot.add_cog(Reminders(bot))
