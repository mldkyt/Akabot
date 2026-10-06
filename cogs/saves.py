from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Message,
    SlashCommandGroup,
    message_command,
)
from discord.ext.pages import Paginator
from sqlalchemy import delete, insert, select

from database import engine, saves


class Saves(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    saves_group = SlashCommandGroup(name="saves", description="Personal saves commands")

    @saves_group.command(name="list")
    async def list_saves(self, ctx: ApplicationContext):
        """List your personal saves"""

        with engine.begin() as c:
            saves_db = c.execute(
                select(saves.c.link)
                .where(saves.c.uid == str(ctx.user.id))
                .order_by(saves.c.id)
            ).fetchall()

        if len(saves_db) == 0:
            await ctx.respond("You have no saves", ephemeral=True)
            return

        pages = []
        current_page = []
        i = 1

        for save in saves_db:
            current_page.append(f"{i}. {save[0]}")

            if len(current_page) >= 5:
                pages.append("\n".join(current_page))
                current_page = []

        if len(current_page) > 0:
            pages.append("\n".join(current_page))

        pager = Paginator(pages)
        await pager.respond(ctx.interaction, ephemeral=True)

    @saves_group.command(name="delete")
    async def delete_save(self, ctx: ApplicationContext, num: int):
        """Delete a save. The number is the same one as in the list."""

        with engine.begin() as c:
            all_saves = c.execute(
                select(saves.c.id, saves.c.link)
                .where(saves.c.uid == str(ctx.user.id))
                .order_by(saves.c.id)
            ).fetchall()

        if num < 1 or num > len(all_saves):
            await ctx.respond("Not found", ephemeral=True)
            return

        with engine.begin() as c:
            c.execute(delete(saves).where(saves.c.id == all_saves[num - 1][0]))

        await ctx.respond(f"Deleted save {all_saves[num - 1][1]}", ephemeral=True)

    @message_command(name="Save")
    async def save_message(self, ctx: ApplicationContext, message: Message):
        """Save a message"""

        with engine.begin() as c:
            c.execute(insert(saves).values(uid=str(ctx.user.id), link=message.jump_url))

        await ctx.respond("Post saved", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Saves(bot))
