from discord import Cog, Bot, Member

from utils.docs import Docs
from utils.roles_on_join import apply_roles, setting_roles_on_join
from utils.server_settings import settings


class RolesOnJoin(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member):
        await apply_roles(member)


def setup(bot: Bot):
    bot.add_cog(RolesOnJoin(bot))

    settings.add_setting(
        setting_roles_on_join
    )


def docs():
    return str(
        Docs(
            name="Roles On Join",
            description="Add roles to members who join the server",
            settings=[
                setting_roles_on_join
            ]
        )
    )
