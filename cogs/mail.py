from discord import Cog, Bot, SlashCommandGroup, ApplicationContext
from discord.ext.pages import Paginator

from utils.mail import get_unread_mail, mark_as_read, get_all_mail, get_mail_by_id, append_mail_footer
from utils.message_appends import message_appends, MessageAppend


class Mail(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    mail_group = SlashCommandGroup("mail")

    @mail_group.command()
    async def read(self, ctx: ApplicationContext, mail: int | None = None):
        if mail is None:
            unread_mail = get_unread_mail(str(ctx.user.id))
            if len(unread_mail) == 0:
                await ctx.respond("No unread mail found.", ephemeral=True)
                return

            show_this = unread_mail[0]
            mark_as_read(str(ctx.user.id), show_this[0])
        else:
            show_this = get_mail_by_id(mail)
            if show_this is None:
                await ctx.respond("This mail was not found", ephemeral=True)
                return

        await ctx.respond(f"{show_this[1]}\n\n-# -{show_this[2]} on {str(show_this[3])}", ephemeral=True)

    @mail_group.command()
    async def list(self, ctx: ApplicationContext):
        mail = get_all_mail(str(ctx.user.id))

        if len(mail) == 0:
            await ctx.respond("No mail found.", ephemeral=True)
            return

        default_page = "Do `/mail read [number]` in order to read a mail.\n\n"

        pages: list[str] = []
        current_page = default_page

        for i in mail:
            if i[1].startswith("#"):
                current_page += "- [" + str(i[0]) + "] "
                if not i[3]:
                    current_page += "**"
                current_page += i[1].split("\n")[0][2:]
                if not i[3]:
                    current_page += "**"
                current_page += "\n"
            else:
                current_page += "- [" + str(i[0]) + "] "
                if not i[3]:
                    current_page += "**"
                current_page += i[1].split("\n")[0][:50]
                if not i[3]:
                    current_page += "**"
                current_page += "\n"

            if len(current_page) > 1000:
                pages.append(current_page)
                current_page = default_page

        if len(current_page) > 0:
            pages.append(current_page)

        paginator = Paginator(pages)
        await paginator.respond(ctx.interaction, ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Mail(bot))

    message_appends.append(
        MessageAppend(process=append_mail_footer)
    )
