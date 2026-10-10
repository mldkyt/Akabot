from enum import Enum

from sqlalchemy import Connection, insert, select, update

from database import kv


class SettingType(Enum):
    NORMAL = 1
    LIST = 2


class KV:
    def __init__(self, name: str, *, default: str | None = None):
        self.name = name
        self.default_value = default

    def default(self) -> str | None:
        return self.default_value

    def get(self, c: Connection, guild_id: int) -> str | None:
        setting = c.execute(
            select(kv.c.value).where(
                (kv.c.uid == str(guild_id))
                & (kv.c.name == self.name)
            )
        ).fetchone()

        if setting is None:
            return self.default_value

        return setting[0]

    def set(self, c: Connection, guild_id: int, value: str):
        setting = c.execute(
            select(kv.c.value).where(
                (kv.c.uid == str(guild_id))
                & (kv.c.name == self.name)
            )
        ).fetchone()

        if setting is None:
            c.execute(
                insert(kv).values(
                    uid=str(guild_id), name=self.name, value=value
                )
            )
        else:
            c.execute(
                update(kv)
                .values(value=value)
                .where(
                    (kv.c.uid == str(guild_id))
                    & (kv.c.name == self.name)
                )
            )
