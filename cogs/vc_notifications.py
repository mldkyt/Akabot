from discord import Cog, Bot, SlashCommandGroup, ApplicationContext, User, VoiceChannel, Forbidden, Member, VoiceState
from sqlalchemy import select, delete, insert

from database import engine, vc_notifications_all, vc_notifications_user, vc_notifications_channel
from logger import nekona_logger


class VCNotifications(Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    command_grp = SlashCommandGroup(name="vc_notifications", description="Subscribe to voice channel notifications")

    @command_grp.command(name="all_notifications", description="Subscribe to ALL voice channel join notifications")
    async def set_all_notifications(self, ctx: ApplicationContext, subscribed: bool):
        with engine.begin() as c:
            current_subscribed = c.execute(
                select(vc_notifications_all)
                .where((vc_notifications_all.c.uid == str(ctx.user.id)) & (
                            vc_notifications_all.c.gid == str(ctx.guild.id)))
            ).fetchone() is not None

            if subscribed and not current_subscribed:
                c.execute(
                    insert(vc_notifications_all)
                    .values(uid=str(ctx.user.id), gid=str(ctx.guild.id))
                )

                await ctx.respond("Subscribed to all notifications", ephemeral=True)
                return

            if not subscribed and current_subscribed:
                c.execute(
                    delete(vc_notifications_all)
                    .where((vc_notifications_all.c.uid == str(ctx.user.id)) & (
                                vc_notifications_all.c.gid == str(ctx.guild.id)))
                )

                await ctx.respond("Unsubscribed from all notifications", ephemeral=True)
                return

            if subscribed and current_subscribed:
                await ctx.respond("You are already subscribed to all notifications", ephemeral=True)
            else:
                await ctx.respond("You aren't subscribed to any notifications", ephemeral=True)

    @command_grp.command(name="sub_user", description="Subscribe to notifications from a specific user")
    async def sub_user(self, ctx: ApplicationContext, user: User):
        with engine.begin() as c:
            if c.execute(
                    select(vc_notifications_user)
                            .where((vc_notifications_user.c.uid == str(ctx.user.id)) &
                                   (vc_notifications_user.c.gid == str(ctx.guild.id)) &
                                   (vc_notifications_user.c.tid == str(user.id)))
            ).fetchone() is not None:
                await ctx.respond(f"You are already subscribed to notifications from {user.mention}", ephemeral=True)
                return

            c.execute(
                insert(vc_notifications_user)
                .values(uid=str(ctx.user.id), gid=str(ctx.guild.id), tid=str(user.id))
            )

            await ctx.respond(f"Subscribed to notifications from {user.mention}", ephemeral=True)

    @command_grp.command(name="unsub_user", description="Unsubscribe from notifications from a specific user")
    async def unsub_user(self, ctx: ApplicationContext, user: User):
        with engine.begin() as c:
            if c.execute(
                    select(vc_notifications_user)
                            .where((vc_notifications_user.c.uid == str(ctx.user.id)) &
                                   (vc_notifications_user.c.gid == str(ctx.guild.id)) &
                                   (vc_notifications_user.c.tid == str(user.id)))
            ).fetchone() is None:
                await ctx.respond(f"You are not subscribed to notifications from {user.mention}", ephemeral=True)
                return

            c.execute(
                delete(vc_notifications_user)
                .where((vc_notifications_user.c.uid == str(ctx.user.id)) &
                       (vc_notifications_user.c.gid == str(ctx.guild.id)) &
                       (vc_notifications_user.c.tid == str(user.id)))
            )

            await ctx.respond(f"Unsubscribed from {user.mention} notifications", ephemeral=True)

    @command_grp.command(name="sub_channel", description="Subscribe to notifications from a specific channel")
    async def sub_channel(self, ctx: ApplicationContext, channel: VoiceChannel):
        with engine.begin() as c:
            if c.execute(
                    select(vc_notifications_channel)
                            .where((vc_notifications_channel.c.uid == str(ctx.user.id)) &
                                   (vc_notifications_channel.c.gid == str(ctx.guild.id)) &
                                   (vc_notifications_channel.c.tid == str(channel.id)))
            ).fetchone() is not None:
                await ctx.respond(f"You are already subscribed to notifications from {channel.mention}", ephemeral=True)
                return

            c.execute(
                insert(vc_notifications_channel)
                .values(uid=str(ctx.user.id), gid=str(ctx.guild.id), tid=str(channel.id))
            )

            await ctx.respond(f"Subscribed to notifications from {channel.mention}", ephemeral=True)

    @command_grp.command(name="unsub_channel", description="Unsubscribe from notifications from a specific channel")
    async def unsub_channel(self, ctx: ApplicationContext, channel: VoiceChannel):
        with engine.begin() as c:
            if c.execute(
                    select(vc_notifications_channel)
                            .where((vc_notifications_channel.c.uid == str(ctx.user.id)) &
                                   (vc_notifications_channel.c.gid == str(ctx.guild.id)) &
                                   (vc_notifications_channel.c.tid == str(channel.id)))
            ).fetchone() is None:
                await ctx.respond(f"You are not subscribed to notifications from {channel.mention}", ephemeral=True)
                return

            c.execute(
                delete(vc_notifications_channel)
                .where((vc_notifications_channel.c.uid == str(ctx.user.id)) &
                       (vc_notifications_channel.c.gid == str(ctx.guild.id)) &
                       (vc_notifications_channel.c.tid == str(channel.id)))
            )

            await ctx.respond(f"Unsubscribed from {channel.mention} notifications", ephemeral=True)

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        with engine.begin() as c:
            if before.channel is None and after.channel is not None:
                nekona_logger.debug("[VC notifications] %s joined %s", member.display_name, after.channel.name)

                sent_to = []

                # Member joined
                for i in c.execute(
                        select(vc_notifications_all.c.uid)
                                .where(vc_notifications_all.c.gid == str(member.guild.id))
                ).fetchall():
                    try:
                        dm_target = member.guild.get_member(int(i[0]))
                        if dm_target is not None:
                            nekona_logger.debug(
                                "[VC notifications] DMing %s about join in %s because of all notifications",
                                dm_target.display_name, after.channel.name)
                            await dm_target.send(f"{member.mention} has joined {after.channel.mention}\n"
                                                 f"-# You received this DM because you're subscribed to all notifications from [{member.guild.name}]({member.guild.jump_url})")
                            sent_to.append(i[0])
                    except Forbidden:
                        pass

                for i in c.execute(
                        select(vc_notifications_user.c.uid)
                                .where((vc_notifications_user.c.tid == str(member.id)) &
                                       (vc_notifications_user.c.gid == str(member.guild.id)))
                ).fetchall():
                    try:
                        if i[0] in sent_to:
                            continue

                        dm_target = member.guild.get_member(int(i[0]))
                        if dm_target is not None:
                            nekona_logger.debug(
                                "[VC notifications] DMing %s about join in %s because of member notifications",
                                dm_target.display_name, after.channel.name)
                            await dm_target.send(f"{member.mention} has joined {after.channel.mention}\n"
                                                 f"-# You received this DM because you're subscribed to {member.mention}'s VC notifications in [{member.guild.name}]({member.guild.jump_url})")
                            sent_to.append(i[0])
                    except Forbidden:
                        pass

                for i in c.execute(
                        select(vc_notifications_channel.c.uid)
                                .where((vc_notifications_channel.c.tid == str(after.channel.id)) &
                                       (vc_notifications_channel.c.gid == str(member.guild.id)))
                ).fetchall():
                    try:
                        if i[0] in sent_to:
                            continue

                        dm_target = member.guild.get_member(int(i[0]))
                        if dm_target is not None:
                            nekona_logger.debug(
                                "[VC notifications] DMing %s about join in %s because of channel notifications",
                                dm_target.display_name, after.channel.name)
                            await dm_target.send(f"{member.mention} has joined {after.channel.mention}\n"
                                                 f"-# You received this DM because you're subscribed to {after.channel.mention}'s VC notifications")
                            sent_to.append(i[0])
                    except Forbidden:
                        pass


def setup(bot: Bot):
    bot.add_cog(VCNotifications(bot))
