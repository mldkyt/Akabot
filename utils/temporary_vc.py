from random import randint

from discord import Member, VoiceState
from sqlalchemy import delete, insert, select

from database import engine, temporary_vcs
from utils.premium import get_limit
from utils.server_settings import ServerSetting, SettingType

setting_temporary_vcs = ServerSetting(
    name="Temporary VCs",
    setting_type=SettingType.LIST,
)


async def h_join_channel(member: Member, after: VoiceState):
    # Handle joining creator channel

    with engine.begin() as c:
        temporary_vcs_ids = setting_temporary_vcs.get(c, member.guild.id)

    if str(after.channel.id) not in temporary_vcs_ids:
        return

    with engine.begin() as c:
        existing = c.execute(
            select(temporary_vcs.c.cid).where(temporary_vcs.c.gid == str(member.guild.id))
        ).fetchall()

        # Drop rows whose channel no longer exists (deleted by hand, by a
        # moderator or by an earlier run), otherwise the free plan limit
        # never recovers once it has been hit once.
        stale = []
        for row in existing:
            try:
                channel_id = int(row[0])
            except (TypeError, ValueError):
                stale.append(row[0])
                continue

            if member.guild.get_channel(channel_id) is None:
                stale.append(row[0])

        if stale:
            c.execute(
                delete(temporary_vcs).where(
                    (temporary_vcs.c.gid == str(member.guild.id))
                    & (temporary_vcs.c.cid.in_(stale))
                )
            )

        limit = get_limit(c, member.guild.id, 3)
        existing_count = len(existing) - len(stale)

    if limit is not None and existing_count >= limit:
        await member.send("The free plan is limited to 3 simultaneous temporary voice channels, so one wasn't created.")
        return

    # Create a channel
    vc = await member.guild.create_voice_channel(name=f"VC {randint(100, 999)}", category=after.channel.category,
                                                 bitrate=after.channel.bitrate, reason="Temporary Voice Channels")

    with engine.begin() as c:
        c.execute(
            insert(temporary_vcs)
            .values(gid=str(member.guild.id), cid=str(vc.id))
        )

    await member.move_to(vc)


async def h_leave_channel(member: Member, before: VoiceState):
    # Handle leaving temporary VC

    with engine.begin() as c:
        temporary_vc_id = c.execute(
            select(temporary_vcs)
            .where((temporary_vcs.c.gid == str(member.guild.id)) & (temporary_vcs.c.cid == str(before.channel.id)))
        ).fetchone()

    if temporary_vc_id is None:
        return

    if len(before.channel.members) == 0:
        await before.channel.delete(reason="Temporary Voice Channels")

        with engine.begin() as c:
            c.execute(
                delete(temporary_vcs).where(
                    (temporary_vcs.c.gid == str(member.guild.id))
                    & (temporary_vcs.c.cid == str(before.channel.id))
                )
            )


async def handle_voice_update(member: Member, before: VoiceState, after: VoiceState):
    # First let's check joining for temporary voice channel creation
    if after.channel and not before.channel:
        await h_join_channel(member, after)

    # Now let's check leaving for temporary voice channel deletion
    if before.channel and not after.channel:
        await h_leave_channel(member, before)

    # Handle moving between channels, it's pretty much leaving the previous and joining the new one
    if before.channel and after.channel and before.channel != after.channel:
        await h_leave_channel(member, before)
        await h_join_channel(member, after)
