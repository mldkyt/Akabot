import datetime

from discord import ApplicationContext, Member, Guild
from sqlalchemy import Connection, select, insert, delete, func

from database import moderator_roles, moderator_warnings, engine, moderator_warning_actions
from logger import akabot_logger
from utils.server_settings import KV

settings_moderator_warnings_expiry = KV(
    "Moderator Warnings Expiry in Days", default="30"
)

def is_user_moderator(c: Connection, m: Member):
    moderators = c.execute(
        select(moderator_roles.c.rid).where(moderator_roles.c.gid == str(m.guild.id))
    ).fetchall()
    for i in moderators:
        for j in m.roles:
            if int(i[0]) == j.id:
                return True

    return False


async def perform_basic_checks(
    c: Connection, ctx: ApplicationContext, user: Member, k: str
) -> tuple[bool, str]:
    if not is_user_moderator(c, ctx.user):
        return False, "You must be moderator in order to use this command"

    # Check if user's role is under ours
    if user.top_role > ctx.user.top_role:
        return False, f"This user has a higher rank than you, can't {k}"

    return True, ""


async def add_warning(user: Member, reason: str) -> int:
    with engine.begin() as c:
        existing = c.execute(
            select(func.max(moderator_warnings.c.case_id))
            .where(
                (moderator_warnings.c.gid == str(user.guild.id))
            )
        ).fetchone()
        if existing is None or existing[0] is None:
            case_id = 1
        else:
            case_id = existing[0] + 1

        c.execute(
            insert(moderator_warnings)
            .values(
                gid=str(user.guild.id),
                uid=str(user.id),
                case_id=case_id,
                message=reason,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )

        await _perform_warning_actions(user.guild, user, case_id)

    return case_id


async def remove_warning(member: Member, case_id: int):
    with engine.begin() as c:
        c.execute(
            moderator_warnings.delete().where(
                (moderator_warnings.c.gid == str(member.guild.id)) &
                (moderator_warnings.c.uid == str(member.id)) &
                (moderator_warnings.c.case_id == case_id)
            )
        )


async def remove_expired_warnings():
    now = datetime.datetime.now(datetime.UTC)

    with engine.begin() as c:
        guild_ids = [
            row[0]
            for row in c.execute(
                select(moderator_warnings.c.gid).distinct()
            ).fetchall()
        ]

        for guild_id in guild_ids:
            expiry_days = int(
                settings_moderator_warnings_expiry.get(c, guild_id) or 0
            )
            if expiry_days <= 0:
                continue

            expiry_date = now - datetime.timedelta(days=expiry_days)
            c.execute(
                delete(moderator_warnings).where(
                    (moderator_warnings.c.gid == guild_id) &
                    (moderator_warnings.c.created_at < expiry_date)
                )
            )


async def list_warnings(member: Member) -> list[dict]:
    with engine.begin() as c:
        warnings = c.execute(
            select(
                moderator_warnings.c.case_id,
                moderator_warnings.c.message,
                moderator_warnings.c.created_at
            ).where(
                (moderator_warnings.c.gid == str(member.guild.id)) &
                (moderator_warnings.c.uid == str(member.id))
            )
        ).fetchall()

    return [
        {
            "case_id": i[0],
            "message": i[1],
            "created_at": i[2]
        }
        for i in warnings
    ]

async def add_warning_action(guild: Guild, action: str, warning_count: int, parameter: str | None = None):
    with engine.begin() as c:
        c.execute(
            insert(moderator_warning_actions).values(
                gid=str(guild.id),
                action=action,
                warning_count=warning_count,
                parameter=parameter
            )
        )

async def remove_warning_action(guild: Guild, action: str, warning_count: int):
    with engine.begin() as c:
        c.execute(
            delete(moderator_warning_actions).where(
                (moderator_warning_actions.c.gid == str(guild.id)) &
                (moderator_warning_actions.c.action == action) &
                (moderator_warning_actions.c.warning_count == warning_count)
            )
        )

async def list_warning_actions(guild: Guild) -> list[dict]:
    with engine.begin() as c:
        actions = c.execute(
            select(
                moderator_warning_actions.c.action,
                moderator_warning_actions.c.warning_count
            ).where(moderator_warning_actions.c.gid == str(guild.id))
        ).fetchall()

    return [
        {
            "action": i[0],
            "warning_count": i[1]
        }
        for i in actions
    ]

async def _perform_warning_actions(guild: Guild, member: Member, case_id: int):
    with engine.begin() as c:
        actions = c.execute(
            select(
                moderator_warning_actions.c.action,
                moderator_warning_actions.c.warning_count,
                moderator_warning_actions.c.parameter
            ).where(moderator_warning_actions.c.gid == str(guild.id))
        ).fetchall()

        warnings = c.execute(
            select(func.count()).where(
                (moderator_warnings.c.gid == str(guild.id)) &
                (moderator_warnings.c.uid == str(member.id))
            )
        ).fetchone()[0]

        for action, warning_count, parameter in actions:
            if warnings == warning_count:
                if action == "kick":
                    if not member.guild.me.guild_permissions.kick_members:
                        akabot_logger.warning(f"Cannot kick {member} in {guild}, missing permissions")
                        continue

                    await member.kick(reason=f"Reached {warning_count} warnings (case {case_id})")
                elif action == "ban":
                    if not member.guild.me.guild_permissions.ban_members:
                        akabot_logger.warning(f"Cannot ban {member} in {guild}, missing permissions")
                        continue

                    await member.ban(reason=f"Reached {warning_count} warnings (case {case_id})")
                elif action == "timeout":
                    if not member.guild.me.guild_permissions.moderate_members:
                        akabot_logger.warning(f"Cannot timeout {member} in {guild}, missing permissions")
                        continue

                    days = int(parameter) if parameter else 1
                    await member.timeout(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days), reason=f"Reached {warning_count} warnings (case {case_id})")