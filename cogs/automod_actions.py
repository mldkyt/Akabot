from discord import AutoModActionExecutionEvent, AutoModRule, Bot, Cog

from logger import nekona_logger
from utils.automod_actions import automod_actions, fetch_actions, handle_automod_actions
from utils.docs import Docs, DocsSetting
from utils.server_settings import settings, SettingType


class AutomodActions(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        for i in self.bot.guilds:
            if i.me.guild_permissions.manage_guild:
                await fetch_actions(i)

    @Cog.listener()
    async def on_auto_moderation_action_execution(
            self, payload: AutoModActionExecutionEvent
    ):
        try:
            await fetch_actions(payload.guild)
            await handle_automod_actions(self.bot, payload)
        except Exception:
            nekona_logger.exception("Automod Action execution error:")

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

    settings.add_settings(automod_actions)


def docs():
    return str(
        Docs(
            name="Automod Actions",
            description="Automod Actions allow you to perform extra actions when an AutoMod rule is triggered.",
            settings=[
                DocsSetting(
                    name="Automod Actions",
                    description="A list of automod actions. Note that only one DM action and one kick/ban/mute action can be set at the same time",
                    setting_type=SettingType.LIST,
                    add_description="Format is usually `name of automod action, action to perform, action parameter(s)`. Actions that can be set are `dm (message)`, `kick (reason)`, `ban (reason)`, `mute (duration, reason)`.",
                    remove_description="Format is `name of automod action, action to remove`. This will remove that action."
                )
            ]
        )
    )
