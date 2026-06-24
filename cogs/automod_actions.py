from discord import AutoModActionExecutionEvent, AutoModRule, Bot, Cog

from logger import akabot_logger
from utils.automod_actions import fetch_actions, handle_automod_actions


class AutomodActions(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    has_init = False

    @Cog.listener()
    async def on_ready(self):
        if not self.has_init:
            for i in self.bot.guilds:
                if i.me.guild_permissions.manage_guild:
                    await fetch_actions(i)

            self.has_init = True

    @Cog.listener()
    async def on_auto_moderation_action_execution(
            self, payload: AutoModActionExecutionEvent
    ):
        try:
            await fetch_actions(payload.guild)
            await handle_automod_actions(self.bot, payload)
        except Exception:
            akabot_logger.exception("Automod Action execution error:")

    @Cog.listener()
    async def on_auto_moderation_rule_create(self, rule: AutoModRule):
        if rule.guild is None:
            return

        if rule.guild.me.guild_permissions.manage_guild:
            await fetch_actions(rule.guild)

    @Cog.listener()
    async def on_auto_moderation_rule_delete(self, rule: AutoModRule):
        if rule.guild is None:
            return

        if rule.guild.me.guild_permissions.manage_guild:
            await fetch_actions(rule.guild)

    @Cog.listener()
    async def on_auto_moderation_rule_update(self, rule: AutoModRule):
        if rule.guild is None:
            return

        if rule.guild.me.guild_permissions.manage_guild:
            await fetch_actions(rule.guild)


def setup(bot: Bot):
    bot.add_cog(AutomodActions(bot))
