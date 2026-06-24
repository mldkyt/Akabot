import os

from discord import Cog, Bot, ApplicationContext, slash_command, default_permissions, AutoModRule, Guild, Role
from discord.abc import GuildChannel

from utils.web import sync_guild, generate_token

WEB_DOMAIN = os.getenv("WEB_DOMAIN", "akabot.mldchan.dev")


class Website(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        super().__init__()

    @Cog.listener()
    async def on_ready(self):
        for i in self.bot.guilds:
            await sync_guild(i)

    @Cog.listener()
    async def on_auto_moderation_rule_create(self, rule: AutoModRule):
        if rule.guild is not None:
            await sync_guild(rule.guild)

    @Cog.listener()
    async def on_auto_moderation_rule_delete(self, rule: AutoModRule):
        if rule.guild is not None:
            await sync_guild(rule.guild)

    @Cog.listener()
    async def on_auto_moderation_rule_update(self, rule: AutoModRule):
        if rule.guild is not None:
            await sync_guild(rule.guild)

    @Cog.listener()
    async def on_guild_channel_update(self, before: GuildChannel, after: GuildChannel):
        await sync_guild(after.guild)

    @Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        await sync_guild(channel.guild)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        await sync_guild(channel.guild)

    @Cog.listener()
    async def on_guild_update(self, before: Guild, after: Guild):
        await sync_guild(after)

    @Cog.listener()
    async def on_guild_role_create(self, role: Role):
        await sync_guild(role.guild)

    @Cog.listener()
    async def on_guild_role_delete(self, role: Role):
        await sync_guild(role.guild)

    @Cog.listener()
    async def on_guild_role_update(self, before: Role, after: Role):
        await sync_guild(after.guild)

    @slash_command()
    @default_permissions(manage_guild=True)
    async def settings(self, ctx: ApplicationContext):
        """Open the web settings"""
        token = generate_token(ctx.guild, ctx.user)
        await ctx.respond(f"https://{WEB_DOMAIN}/settings?token={token}")


def setup(bot: Bot):
    bot.add_cog(Website(bot))
