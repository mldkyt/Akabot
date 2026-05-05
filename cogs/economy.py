from discord import Cog, Bot, SlashCommandGroup, ApplicationContext, IntegrationType, option, User

from utils.economy import work, get_money, transfer, rob, pay, gamble
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


def setup(bot: Bot):
    bot.add_cog(Economy(bot))
