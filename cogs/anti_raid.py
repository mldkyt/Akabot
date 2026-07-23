from discord import Bot, Cog, Member, Message

from utils.anti_raid import verify_member


class AntiRaid(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member):
        await verify_member(member)


def setup(bot: Bot):
    bot.add_cog(AntiRaid(bot))
