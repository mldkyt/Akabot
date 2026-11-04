import datetime

from discord import ApplicationContext, Member
from sqlalchemy import Connection, select, insert, delete, func

from database import moderator_roles, moderator_warnings, engine
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

    return case_id


async def remove_warning(member: Member, case_id: int):
    with engine.begin() as c:
        c.execute(
            moderator_warnings.delete().where(
                (moderator_warnings.c.uid == str(member.id)) &
                (moderator_warnings.c.case_id == case_id)
            )
        )


async def remove_expired_warnings():
    with engine.begin() as c:
        expiry_days = int(settings_moderator_warnings_expiry.get(c, "0"))
        if expiry_days <= 0:
            return

        expiry_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            days=expiry_days
        )
        c.execute(
            delete(moderator_warnings).where(
                moderator_warnings.c.created_at < expiry_date
            )
        )


async def list_warnings(member: Member) -> list[dict]:
    with engine.begin() as c:
        warnings = c.execute(
            select(
                moderator_warnings.c.case_id,
                moderator_warnings.c.message,
                moderator_warnings.c.created_at
            ).where(moderator_warnings.c.uid == str(member.id))
        ).fetchall()

    return [
        {
            "case_id": i[0],
            "message": i[1],
            "created_at": i[2]
        }
        for i in warnings
    ]
