from sqlalchemy import Connection, insert, select, update

from database import leveling
from utils.server_settings import get_server_setting


def get_xp(c: Connection, uid: int, gid: int) -> int:
    result = c.execute(
        select(leveling.c.xp)
            .where((leveling.c.uid == uid) & (leveling.c.gid == gid))
    ).fetchone()

    if not result:
        return 0

    return result[0]

def add_xp(c: Connection, uid: int, gid: int):
    xp_per_msg = get_server_setting(c, gid, "Leveling XP per message")

    existing = c.execute(
        select(leveling.c.xp)
            .where((leveling.c.uid == uid) & (leveling.c.gid == gid))
    ).fetchone()

    if existing is None:
        c.execute(
            insert(leveling).values(uid=uid, gid=gid, xp=0)
        )

    c.execute(
        update(leveling)
            .where((leveling.c.uid == uid) & (leveling.c.gid == gid))
            .values(xp=(existing[0] or 0) + int(xp_per_msg))
    )

def calculate_level(c: Connection, uid: int, xp: int) -> int:
    xp_per_level = int(get_server_setting(c, uid, "Leveling XP per level"))
    return (xp // xp_per_level) + 1
