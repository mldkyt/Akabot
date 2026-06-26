from discord import Cog, Bot, Member

from utils.roles_on_join import apply_roles


class RolesOnJoin(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member):
        await apply_roles(member)


def setup(bot: Bot):
    bot.add_cog(RolesOnJoin(bot))
