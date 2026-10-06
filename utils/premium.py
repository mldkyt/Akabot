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
        select(premium_guilds.c.premium_until, premium_guilds.c.unlimited).where(
            premium_guilds.c.gid == str(guild_id)
        )
    ).fetchone()

    if row is None:
        return False

    return row[1] or row[0] > datetime.datetime.now()


def premium_required(c: Connection, guild_id: int) -> bool:
    return not has_premium(c, guild_id)


def get_limit(c: Connection, guild_id: int, free_limit: int) -> int | None:
    if has_premium(c, guild_id):
        return None

    return free_limit


def redeem_token(c: Connection, guild_id: int, code: str) -> tuple[bool, str]:
    code = code.strip().upper()

    token = c.execute(
        select(premium_tokens.c.duration_days, premium_tokens.c.unlimited)
        .where(premium_tokens.c.code == code)
    ).fetchone()

    if token is None:
        return False, "invalid code"

    now = datetime.datetime.now()

    # Claim the code before granting anything. The IS NULL predicate makes the
    # claim atomic, so a concurrent redeem of the same code updates zero rows
    # instead of both callers extending premium.
    claimed = c.execute(
        update(premium_tokens)
        .where(
            (premium_tokens.c.code == code)
            & (premium_tokens.c.redeemed_gid.is_(None))
        )
        .values(redeemed_gid=str(guild_id), redeemed_at=now)
    )
    if claimed.rowcount == 0:
        return False, "code was already used"

    existing = c.execute(
        select(premium_guilds.c.premium_until, premium_guilds.c.unlimited).where(
            premium_guilds.c.gid == str(guild_id)
        )
    ).fetchone()

    if existing is not None:
        base = max(existing[0], now)
    else:
        base = now

    if token[1]:
        new_until = base
    else:
        new_until = base + datetime.timedelta(days=token[0])

    if existing is not None:
        c.execute(
            update(premium_guilds)
            .where(premium_guilds.c.gid == str(guild_id))
            .values(activated_at=now, premium_until=new_until, unlimited=existing[1] or bool(token[1]))
        )
    else:
        c.execute(
            insert(premium_guilds).values(
                gid=str(guild_id),
                premium_until=new_until,
                activated_at=now,
                unlimited=bool(token[1]),
            )
        )

    if token[1]:
        return True, "unlimited"
    return True, new_until.strftime("%Y-%m-%d")


def generate_tokens(count: int, duration_days: int, prefix: str = "AKA", unlimited: bool = False) -> list[str]:
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
                    unlimited=unlimited,
                    created_at=now,
                )
            )
            codes.append(code)

    return codes


def is_owner(user_id: int) -> bool:
    owner = os.getenv("BOT_OWNER_ID", "")
    return owner != "" and str(user_id) == owner


def get_premium_context(c: Connection, guild_id: int) -> dict:
    if not premium_enabled():
        return {
            "enabled": False,
            "active": True,
            "unlimited": False,
            "premium_only": False,
        }

    row = c.execute(
        select(premium_guilds.c.premium_until, premium_guilds.c.unlimited).where(
            premium_guilds.c.gid == str(guild_id)
        )
    ).fetchone()

    unlimited = row is not None and bool(row[1])
    active = unlimited or (row is not None and row[0] > datetime.datetime.now())

    return {
        "enabled": True,
        "active": active,
        "unlimited": unlimited,
        "premium_only": not active,
    }


def usage_bar(c: Connection, guild_id: int, name: str, usage: int, free_limit: int) -> dict:
    if not premium_enabled():
        return None

    limit = get_limit(c, guild_id, free_limit)
    active = has_premium(c, guild_id)

    if limit is None:
        percent = 100
        text = f"{usage}/unlimited"
    elif limit == 0:
        percent = 0
        text = f"{usage}/{limit}"
    else:
        percent = min(100, round(usage / limit * 100))
        text = f"{usage}/{limit} ({percent}%)"

    return {
        "enabled": True,
        "active": active,
        "name": name,
        "usage": usage,
        "limit": limit,
        "percent": percent,
        "text": text,
    }