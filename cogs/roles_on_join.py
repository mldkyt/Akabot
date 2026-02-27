from discord import Cog, Bot, Member

from utils.docs import Docs, DocsSetting
from utils.roles_on_join import apply_roles, setting_roles_on_join
from utils.server_settings import settings, SettingType


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
    return Docs(
        name="Roles On Join",
        description="Add roles to members who join the server",
        settings=[
            DocsSetting(
                name="Roles On Join",
                description="The roles to be added to members on join",
                setting_type=SettingType.LIST,
                add_description="Add a role. Accepts a role mention, ID or name. New members will get this role when they join",
                remove_description="Remove a role. Accepts a role mention, ID or name. New members will no longer get this role when they join"
            )
        ]
    )
