import datetime

from discord import Cog, Bot, SlashCommandGroup, ApplicationContext, IntegrationType, option, User, Guild
from sqlalchemy import delete, func, select, insert

from database import engine, invite_redeem_codes, invite_redeem_guild_lock, invite_redeem_time_lock
from utils.economy import work, get_money, transfer, rob, pay, gamble, update_money
from utils.message_appends import apply_appends


# economy
# banks and wallets ig
# add work (limit how many times per hour)

class Economy(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    economy_commands = SlashCommandGroup(name="economy", description="Economy commands")

    @economy_commands.command(integration_types=[IntegrationType.user_install, IntegrationType.guild_install])
    async def work(self, ctx: ApplicationContext):
        ok, earned_or_error = await work(ctx)

        if ok:
            await ctx.respond(apply_appends(ctx.user.id, f"You went to work and earned {earned_or_error} NekoCoins."),
                              ephemeral=True)
        else:
            await ctx.respond(apply_appends(ctx.user.id, earned_or_error), ephemeral=True)

    @economy_commands.command(integration_types=[IntegrationType.user_install, IntegrationType.guild_install])
    async def bal(self, ctx: ApplicationContext):
        wallet, bank = get_money(ctx.user.id)
        await ctx.respond(apply_appends(ctx.user.id,
                                        f"You have {wallet} NekoCoins in your wallet and {bank} NekoCoins in your bank account."),
                          ephemeral=True)

    @economy_commands.command(integration_types=[IntegrationType.user_install, IntegrationType.guild_install])
    @option(name="target", choices=["bank", "wallet"])
    async def transfer(self, ctx: ApplicationContext, target: str, amount: int):
        ok, moved_or_error = await transfer(ctx, target, amount)
        if ok:
            await ctx.respond(
                apply_appends(ctx.user.id, f"Successfully transferred {moved_or_error} NekoCoins to {target}"),
                ephemeral=True)
        else:
            await ctx.respond(apply_appends(ctx.user.id, moved_or_error), ephemeral=True)

    @economy_commands.command(integration_types=[IntegrationType.user_install, IntegrationType.guild_install])
    async def rob(self, ctx: ApplicationContext, target: User):
        ok, robbed_or_error = await rob(ctx, target)

        if ok:
            await ctx.respond(apply_appends(ctx.user.id,
                                            f"You successfully robbed {target.mention} for {robbed_or_error} NekoCoins."),
                              ephemeral=True)
        else:
            await ctx.respond(apply_appends(ctx.user.id, robbed_or_error), ephemeral=True)

    @economy_commands.command(integration_types=[IntegrationType.user_install, IntegrationType.guild_install])
    async def pay(self, ctx: ApplicationContext, target: User, amount: int):
        ok, error = await pay(ctx, target, amount)
        if not ok:
            await ctx.respond(apply_appends(ctx.user.id, error), ephemeral=True)

    @economy_commands.command(integration_types=[IntegrationType.user_install, IntegrationType.guild_install])
    async def gamble(self, ctx: ApplicationContext, amount: int):
        ok, error = await gamble(ctx, amount)
        if not ok:
            await ctx.respond(apply_appends(ctx.user.id, error), ephemeral=True)

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        with engine.begin() as c:
            c.execute(
                insert(invite_redeem_codes).values(gid=str(guild.id), expiry=datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=30))
            )

    @economy_commands.command()
    async def redeem_invite(self, ctx: ApplicationContext):
        """If you invite the bot into a server, redeem 1000 AkaCoins!"""
        if not ctx.user.guild_permissions.manage_guild:
            await ctx.respond("This only is available to people who can invite the bot into servers (Manage Server permission)", ephemeral=True)
            return

        with engine.begin() as c:
            c.execute(
                delete(invite_redeem_codes)
                .where(invite_redeem_codes.c.expiry < func.now())
            )
            c.execute(
                delete(invite_redeem_time_lock)
                .where(invite_redeem_time_lock.c.expiry < func.now())
            )

            invite_code = c.execute(
                select(invite_redeem_codes.c.gid)
                .where(invite_redeem_codes.c.gid == str(ctx.guild.id))
            ).fetchone()

            redeem_lock = c.execute(
                select(invite_redeem_time_lock)
                .where(invite_redeem_time_lock.c.uid == str(ctx.user.id))
            ).fetchone()

            guild_lock = c.execute(
                select(invite_redeem_guild_lock)
                .where(invite_redeem_guild_lock.c.gid == str(ctx.guild.id))
            ).fetchone()

        if not invite_code:
            await ctx.respond("You have not invited the bot into a server yet, or your invite has expired. Please invite the bot into a server and try again.", ephemeral=True)
            return

        if redeem_lock:
            await ctx.respond("You have already redeemed your invite reward. You can only redeem once per user.", ephemeral=True)
            return

        if guild_lock:
            await ctx.respond("This server has already redeemed the invite reward. You can only redeem once per server.", ephemeral=True)
            return

        with engine.begin() as c:
            c.execute(
                insert(invite_redeem_time_lock).values(uid=str(ctx.user.id), expiry=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=7))
            )
            c.execute(
                insert(invite_redeem_guild_lock).values(gid=str(ctx.guild.id))
            )
            c.execute(
                delete(invite_redeem_codes)
                .where(invite_redeem_codes.c.gid == str(ctx.guild.id))
            )

        update_money(ctx.user.id, "wallet", 1000)

        await ctx.respond("You have successfully redeemed your 1000 AkaCoins for inviting the bot!", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Economy(bot))
