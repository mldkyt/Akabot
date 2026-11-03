from discord import Cog, Bot, Guild, TextChannel

from logger import akabot_logger


class InviteMessage(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        try:
            # Attempt to find general, else fallback to first channel with send permission
            channel: TextChannel | None = None

            for c in guild.text_channels:
                perms = c.permissions_for(guild.me)
                if c.name.lower() == "general" and perms.send_messages and perms.view_channel:
                    channel = c
                    break
            else:
                for c in guild.text_channels:
                    perms = c.permissions_for(guild.me)
                    if perms.send_messages and perms.view_channel:
                        channel = c
                        break

            if channel is None:
                return

            # Send welcome message
            await channel.send("# Welcome to Akabot!\n\n"
                               "Thank you for inviting me to your server! I am a multipurpose bot with many features.\n\n"
                               "## Set me up!\n\n"
                               "Use the `/settings` command from Akabot to get a unique link to open the dashboard for your server. From there, you can configure Akabot to your liking, including setting up economy, leveling, and more.\n\n"
                               "## Redeem your reward\n\n"
                               "You can redeem 1000 AkaCoins for inviting me using the `/economy redeem_invite` command.")
        except Exception:
            akabot_logger.exception("Error when trying to send a welcome message")


def setup(bot: Bot):
    bot.add_cog(InviteMessage(bot))
