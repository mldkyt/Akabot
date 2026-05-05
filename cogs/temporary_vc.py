from discord import Cog, Bot, VoiceState, Member, SlashCommandGroup, ApplicationContext, PermissionOverwrite
from sqlalchemy import select

from database import engine, temporary_vcs
from utils.docs import Docs
from utils.message_appends import apply_appends
from utils.server_settings import settings
from utils.temporary_vc import handle_voice_update, setting_temporary_vcs


class TemporaryVC(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState,
                                    after: VoiceState):
        await handle_voice_update(member, before, after)

    temporary_vc_commands = SlashCommandGroup(name="temporary_vcs", description="Manage temporary voice channels")

    @temporary_vc_commands.command()
    async def set_private(self, ctx: ApplicationContext, private: bool):
        if not ctx.user.voice:
            await ctx.respond("You need to be in a voice channel")
            return

        with engine.begin() as c:
            temporary_vc = c.execute(
                select(temporary_vcs)
                .where((temporary_vcs.c.gid == str(ctx.guild.id)) & (
                            temporary_vcs.c.cid == str(ctx.user.voice.channel.id)))
            ).fetchone()

        if temporary_vc is None:
            await ctx.respond("You are not in a temporary VC")
            return

        if private:
            # Update chat perms
            permissions = {
                ctx.guild.default_role: PermissionOverwrite(view_channel=False, connect=False, speak=False,
                                                            send_messages=False),
                ctx.guild.me: PermissionOverwrite(view_channel=True, connect=True, speak=True, send_messages=True),
            }

            for i in ctx.user.voice.channel.members:
                # noinspection PyTypeChecker
                permissions[i] = PermissionOverwrite(view_channel=True, connect=True, speak=True, send_messages=True)

            await ctx.user.voice.channel.edit(overwrites=permissions)

        else:
            await ctx.user.voice.channel.edit(overwrites={})

        await ctx.respond(apply_appends(ctx.user.id, "Updated private VC state successfully"), ephemeral=True)

    @temporary_vc_commands.command()
    async def add_private(self, ctx: ApplicationContext, member: Member):
        if not ctx.user.voice:
            await ctx.respond("You need to be in a voice channel", ephemeral=True)
            return

        with engine.begin() as c:
            temporary_vc = c.execute(
                select(temporary_vcs)
                .where((temporary_vcs.c.gid == str(ctx.guild.id)) & (
                        temporary_vcs.c.cid == str(ctx.user.voice.channel.id)))
            ).fetchone()

        if temporary_vc is None:
            await ctx.respond("You are not in a temporary VC", ephemeral=True)
            return

        if ctx.user.voice.channel.overwrites_for(ctx.guild.me).connect is None:
            await ctx.respond("This channel is not a private channel, cannot add members", ephemeral=True)
            return

        await ctx.user.voice.channel.set_permissions(member,
                                                     overwrite=PermissionOverwrite(view_channel=True, connect=True,
                                                                                   speak=True, send_messages=True))
        await ctx.respond(apply_appends(ctx.user.id, f"Added member {member.mention} to temporary VC successfully"),
                          ephemeral=True)

    @temporary_vc_commands.command()
    async def remove_private(self, ctx: ApplicationContext, member: Member):
        if not ctx.user.voice:
            await ctx.respond("You need to be in a voice channel", ephemeral=True)
            return

        with engine.begin() as c:
            temporary_vc = c.execute(
                select(temporary_vcs)
                .where((temporary_vcs.c.gid == str(ctx.guild.id)) & (
                        temporary_vcs.c.cid == str(ctx.user.voice.channel.id)))
            ).fetchone()

        if temporary_vc is None:
            await ctx.respond("You are not in a temporary VC", ephemeral=True)
            return

        if len(ctx.user.voice.channel.members) == 1 and ctx.user.voice.channel.members[0] == member:
            await ctx.respond("Cannot kick last member; Disconnect instead", ephemeral=True)
            return

        if ctx.user.voice.channel.overwrites_for(ctx.guild.me).connect is None:
            await ctx.respond("This channel is not a private channel, cannot remove members", ephemeral=True)
            return

        if member in ctx.user.voice.channel.members:
            await member.move_to(None)

        await ctx.user.voice.channel.set_permissions(member, overwrite=None)
        await ctx.respond(apply_appends(ctx.user.id, f"Removed {member.mention} from temporary VC successfully"),
                          ephemeral=True)

def setup(bot: Bot):
    bot.add_cog(TemporaryVC(bot))

    settings.add_setting(setting_temporary_vcs)


def docs():
    return str(
        Docs(
            name="Temporary VC",
            description="Temporary voice channels.",
            settings=[
                setting_temporary_vcs
            ]
        )
    )
