import datetime
import os
import random
import string

from sqlalchemy import Connection, insert, select, update

from database import engine, premium_guilds, premium_tokens


def premium_enabled() -> bool:
    return os.getenv("AKABOT_PREMIUM", "0") == "1"


def has_premium(c: Connection, guild_id: int) -> bool:
    if not premium_enabled():
        return True

    row = c.execute(
        select(premium_guilds.c.premium_until).where(
            premium_guilds.c.gid == str(guild_id)
        )
    ).fetchone()

    if row is None:
        return False

    return row[0] > datetime.datetime.now()


def premium_required(c: Connection, guild_id: int) -> bool:
    return not has_premium(c, guild_id)


def get_limit(c: Connection, guild_id: int, free_limit: int) -> int | None:
    if has_premium(c, guild_id):
        return None

    return free_limit


def redeem_token(c: Connection, guild_id: int, code: str) -> tuple[bool, str]:
    code = code.strip().upper()

    token = c.execute(
        select(premium_tokens.c.duration_days, premium_tokens.c.redeemed_gid)
        .where(premium_tokens.c.code == code)
    ).fetchone()

    if token is None:
        return False, "invalid code"

    if token[1] is not None:
        return False, "code was already used"

    now = datetime.datetime.now()

    existing = c.execute(
        select(premium_guilds.c.premium_until).where(
            premium_guilds.c.gid == str(guild_id)
        )
    ).fetchone()

    if existing is not None:
        base = max(existing[0], now)
    else:
        base = now

    new_until = base + datetime.timedelta(days=token[0])

    if existing is not None:
        c.execute(
            update(premium_guilds)
            .where(premium_guilds.c.gid == str(guild_id))
            .values(activated_at=now, premium_until=new_until)
        )
    else:
        c.execute(
            insert(premium_guilds).values(
                gid=str(guild_id),
                premium_until=new_until,
                activated_at=now,
            )
        )
    c.execute(
        update(premium_tokens)
        .where(premium_tokens.c.code == code)
        .values(redeemed_gid=str(guild_id), redeemed_at=now)
    )

    return True, new_until.strftime("%Y-%m-%d")


def generate_tokens(count: int, duration_days: int, prefix: str = "AKA") -> list[str]:
    codes = []
    now = datetime.datetime.now()

    with engine.begin() as c:
        for _ in range(count):
            code = f"{prefix}-" + "".join(
                random.choices(string.ascii_uppercase + string.digits, k=12)
            )
            c.execute(
                insert(premium_tokens).values(
                    code=code,
                    duration_days=duration_days,
                    created_at=now,
                )
            )
            codes.append(code)

    return codes


def is_owner(user_id: int) -> bool:
    owner = os.getenv("BOT_OWNER_ID", "")
    return owner != "" and str(user_id) == owner


def get_premium_context(c: Connection, guild_id: int) -> dict:
    return {
        "enabled": premium_enabled(),
        "active": has_premium(c, guild_id),
        "premium_only": premium_required(c, guild_id),
    }