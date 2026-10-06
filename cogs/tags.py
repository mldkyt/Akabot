from discord import Bot, Cog, Message
from sqlalchemy import select

from database import engine, tags


class Tags(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot or not message.guild:
            return

        with engine.begin() as c:
            tags_db = c.execute(
                select(tags.c.keyword, tags.c.content).where(
                    tags.c.guild_id == str(message.guild.id)
                )
            ).fetchall()

            words = message.content.split(" ")
            for tag in tags_db:
                if tag[0] in words:
                    await message.reply(tag[1])


def setup(bot: Bot):
    if not bot.intents.message_content:
        return

    bot.add_cog(Tags(bot))
