from sqlalchemy import Connection, insert, select, update

from database import user_settings as us_table


class UserKV:
    def __init__(
        self,
        name: str,
        default: str,
    ):
        self.name = name
        self.default_value = default

    def default(self) -> list[str] | str:
        return self.default_value

    def get(self, c: Connection, member: int) -> str | list[str]:
        setting = c.execute(
            select(us_table.c.value).where(
                (us_table.c.uid == str(member)) & (us_table.c.name == self.name)
            )
        ).fetchone()

        if setting is None:
            return self.default_value

        return setting[0]

    def set(self, c: Connection, member: int, value: str):
        setting = c.execute(
            select(us_table).where(
                (us_table.c.uid == str(member)) & (us_table.c.name == self.name)
            )
        ).fetchone()

        if setting is None:
            c.execute(
                insert(us_table).values(
                    uid=str(member), name=self.name, value=value
                )
            )
        else:
            c.execute(
                update(us_table)
                .values(value=value)
                .where(
                    (us_table.c.uid == str(member)) & (us_table.c.name == self.name)
                )
            )
