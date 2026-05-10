from discord import Cog, Bot, slash_command, ApplicationContext, Embed, SlashCommandGroup, Member, Color, User, \
    IntegrationType

from database import engine
from utils.fun import yaoi_cache, yuri_cache, nb_embed, ensure_consent, ConsentView, get_consent, \
    setting_allow_rp_commands, setting_disable_yaoi_command, setting_disable_yuri_command
from utils.message_appends import apply_appends
from utils.server_settings import settings


class Fun(Cog):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    @slash_command()
    async def yaoi(self, ctx: ApplicationContext):
        if ctx.guild is not None:
            with engine.begin() as c:
                disable_yaoi = setting_disable_yaoi_command.get_guild(c, ctx.guild)
                if disable_yaoi == "true":
                    await ctx.respond("The yaoi command is disabled in this server", ephemeral=True)
                    return

        yaoi_post = await yaoi_cache.get_yaoibot_post()
        if yaoi_post is None:
            await ctx.respond("Yaoi is unavailable.", ephemeral=True)
            return

        embed = Embed(
            title="Yaoi!",
            image=yaoi_post["files"][0]["url"]
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command()
    async def yuri(self, ctx: ApplicationContext):
        if ctx.guild is not None:
            with engine.begin() as c:
                disable_yuri = setting_disable_yuri_command.get_guild(c, ctx.guild)
                if disable_yuri == "true":
                    await ctx.respond("The yuri command is disabled in this server", ephemeral=True)
                    return

        yuri_post = await yuri_cache.get_yuribot_post()
        if yuri_post is None:
            await ctx.respond("Yuri is unavailable.", ephemeral=True)
            return

        embed = Embed(
            title="Yuri!",
            image=yuri_post["files"][0]["url"]
        )

        await ctx.respond(embed=embed, ephemeral=True)

    rp_group = SlashCommandGroup(name="rp",
                                 integration_types=[IntegrationType.user_install, IntegrationType.guild_install])

    @rp_group.command()
    async def lurk(self, ctx: ApplicationContext):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        lurk = await nb_embed(ctx, "lurk")
        if lurk is None:
            return

        await ctx.respond(embed=lurk)

    @rp_group.command()
    async def shrug(self, ctx: ApplicationContext):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        shrug = await nb_embed(ctx, "shrug")
        if shrug is None:
            return

        await ctx.respond(embed=shrug)

    @rp_group.command()
    async def wave(self, ctx: ApplicationContext):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        wave = await nb_embed(ctx, "wave")
        if wave is None:
            return

        await ctx.respond(embed=wave)

    @rp_group.command()
    async def poke(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 2):
            return

        if target == ctx.user:
            await ctx.respond(apply_appends(ctx.user.id, "You cannot poke yourself!"), ephemeral=True)
            return

        poke = await nb_embed(ctx, "poke", target=target)
        if poke is None:
            return

        await ctx.respond(embed=poke)

    @rp_group.command()
    async def smile(self, ctx: ApplicationContext):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        smile = await nb_embed(ctx, "smile")
        if smile is None:
            return

        await ctx.respond(embed=smile)

    @rp_group.command()
    async def wink(self, ctx: ApplicationContext):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        wink = await nb_embed(ctx, "wink")
        if wink is None:
            return

        await ctx.respond(embed=wink)

    @rp_group.command()
    async def blush(self, ctx: ApplicationContext):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        blush = await nb_embed(ctx, "blush")
        if blush is None:
            return

        await ctx.respond(embed=blush)

    @rp_group.command()
    async def smug(self, ctx: ApplicationContext):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        smug = await nb_embed(ctx, "smug")
        if smug is None:
            return

        await ctx.respond(embed=smug)

    @rp_group.command()
    async def tickle(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 2):
            return

        if target == ctx.user:
            await ctx.respond("You cannot tickle yourself!", ephemeral=True)
            return

        tickle = await nb_embed(ctx, "tickle", target=target)
        if tickle is None:
            return

        await ctx.respond(embed=tickle)

    @rp_group.command()
    async def yeet(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 1):
            return

        if target == ctx.user:
            await ctx.respond("You cannot yeet yourself!", ephemeral=True)
            return

        yeet = await nb_embed(ctx, "yeet", target=target)
        if yeet is None:
            return

        await ctx.respond(embed=yeet)

    @rp_group.command()
    async def highfive(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 1):
            return

        if target == ctx.user:
            await ctx.respond("You cannot give a highfive to yourself!", ephemeral=True)
            return

        highfive = await nb_embed(ctx, "highfive", target=target)
        if highfive is None:
            return

        await ctx.respond(embed=highfive)

    @rp_group.command()
    async def wag(self, ctx: ApplicationContext):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        wag = await nb_embed(ctx, "wag")
        if wag is None:
            return

        await ctx.respond(embed=wag)

    @rp_group.command()
    async def bite(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 3):
            return

        if target == ctx.user:
            await ctx.respond("You cannot bite yourself!", ephemeral=True)
            return

        bite = await nb_embed(ctx, "bite", target=target)
        if bite is None:
            return

        await ctx.respond(embed=bite)

    @rp_group.command()
    async def cuddle(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 2):
            return

        if target == ctx.user:
            await ctx.respond("You cannot cuddle yourself!", ephemeral=True)
            return

        cuddle = await nb_embed(ctx, "cuddle", target=target)
        if cuddle is None:
            return

        await ctx.respond(embed=cuddle)

    @rp_group.command()
    async def kick(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 1):
            return

        if target == ctx.user:
            await ctx.respond("You cannot kick yourself!", ephemeral=True)
            return

        kick = await nb_embed(ctx, "kick", target=target)
        if kick is None:
            return

        await ctx.respond(embed=kick)

    @rp_group.command()
    async def carry(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 1):
            return

        if target == ctx.user:
            await ctx.respond("You cannot carry yourself!", ephemeral=True)
            return

        carry = await nb_embed(ctx, "carry", target=target)
        if carry is None:
            return

        await ctx.respond(embed=carry)

    @rp_group.command()
    async def hug(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 2):
            return

        if target == ctx.user:
            await ctx.respond("You cannot hug yourself!", ephemeral=True)
            return

        hug = await nb_embed(ctx, "hug", target=target)
        if hug is None:
            return

        await ctx.respond(embed=hug)

    @rp_group.command()
    async def bonk(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 1):
            return

        if target == ctx.user:
            await ctx.respond("You cannot bonk yourself!", ephemeral=True)
            return

        bonk = await nb_embed(ctx, "bonk", target=target)
        if bonk is None:
            return

        await ctx.respond(embed=bonk)

    @rp_group.command()
    async def pat(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 2):
            return

        if target == ctx.user:
            await ctx.respond("You cannot pat yourself unfortunately :(", ephemeral=True)
            return

        pat = await nb_embed(ctx, "pat", target=target)
        if pat is None:
            return

        await ctx.respond(embed=pat)

    @rp_group.command()
    async def kiss(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 3):
            return

        if target == ctx.user:
            await ctx.respond("You cannot kiss yourself", ephemeral=True)
            return

        kiss = await nb_embed(ctx, "kiss", target=target)
        if kiss is None:
            return

        await ctx.respond(embed=kiss)

    @rp_group.command()
    async def slap(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 2):
            return

        if target == ctx.user:
            await ctx.respond("You cannot slap yourself", ephemeral=True)
            return

        slap = await nb_embed(ctx, "slap", target=target)
        if slap is None:
            return

        await ctx.respond(embed=slap)

    @rp_group.command()
    async def lappillow(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 2):
            return

        if target == ctx.user:
            await ctx.respond("You cannot lie on your lap :(", ephemeral=True)
            return

        lappillow = await nb_embed(ctx, "lappillow", target=target)
        if lappillow is None:
            return

        await ctx.respond(embed=lappillow)

    @rp_group.command()
    async def handhold(self, ctx: ApplicationContext, target: Member):
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if not await ensure_consent(ctx, target, 3):
            return

        if target == ctx.user:
            await ctx.respond("You cannot handhold yourself", ephemeral=True)
            return

        handhold = await nb_embed(ctx, "handhold", target=target)
        if handhold is None:
            return

        await ctx.respond(embed=handhold)

    @rp_group.command()
    async def consent(self, ctx: ApplicationContext, target: User):
        """Ask for consent with another member"""
        with engine.begin() as c:
            if ctx.guild is not None and setting_allow_rp_commands.get(c, ctx.user) != "true":
                await ctx.respond(apply_appends(ctx.user.id, "RP commands are disabled in this server"), ephemeral=True)
                return

        if ctx.user.id == target.id:
            await ctx.respond(
                apply_appends(ctx.user.id,
                              "Unfortunately you cannot consent to yourself (the commands don't work on yourself either.)"),
                ephemeral=True)
            return

        await ctx.respond(f"{target.mention}", embed=Embed(
            title="Consent",
            description=f"{ctx.user.mention} has asked you to consent to using RP commands from this bot.\n"
                        f"\n"
                        f"You can choose the level of consent according to the levels below:\n"
                        f"**Level 1** - Consent to only fun commands (yeet, highfive, kick, carry, bonk)\n"
                        f"**Level 2** - Consent to commands with more interaction (pat, poke, tickle, cuddle, hug, pat, slap, lappillow)\n"
                        f"**Level 3** - Consent to personal commands (kiss, bite, handhold)",
            color=Color.green()
        ), view=ConsentView(ctx.user, target))

    @rp_group.command()
    async def check_consent(self, ctx: ApplicationContext, target: User):
        """Check if you have consented with somebody"""
        if ctx.user.id == target.id:
            await ctx.respond(
                apply_appends(ctx.user.id,
                              "Unfortunately you cannot consent to yourself (the commands don't work on yourself either.)"),
                ephemeral=True)
            return

        CONSENT_LEVELS = [
            "nothing",
            "yeet, highfive, kick, carry, bonk",
            "pat, poke, tickle, cuddle, hug, pat, slap, lappillow",
            "kiss, bite, handhold"
        ]

        consent_level = await get_consent(ctx.user, target)

        await ctx.respond(apply_appends(ctx.user.id,
                                        f"You and {target} are on consent level {consent_level}: {CONSENT_LEVELS[consent_level]}"),
                          ephemeral=True)


def setup(bot):
    bot.add_cog(Fun(bot))

    settings.add_settings(
        setting_allow_rp_commands,
        setting_disable_yaoi_command,
        setting_disable_yuri_command
    )
