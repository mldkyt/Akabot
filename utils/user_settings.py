from decimal import InvalidOperation
from typing import Callable

from discord import AutocompleteContext, Member
from sqlalchemy import Connection, delete, insert, select, update

from database import user_settings as us_table
from database import user_settings_list as usl_table
from utils.server_settings import SettingType


class UserSetting:
    def __init__(
        self,
        name: str,
        *,
        setting_type: SettingType = SettingType.NORMAL,
        default: str | None = None,
    ):
        self.name = name

        self.setting_type = setting_type

        if self.setting_type == SettingType.NORMAL:
            self.default_value = default
        elif self.setting_type == SettingType.LIST:
            self.default_value = []

    def default(self) -> list[str] | str:
        return self.default_value

    def get(self, c: Connection, member: int) -> str | list[str]:
        if self.setting_type == SettingType.NORMAL:
            setting = c.execute(
                select(us_table.c.value).where(
                    (us_table.c.uid == str(member)) & (us_table.c.name == self.name)
                )
            ).fetchone()

            if setting is None:
                return self.default_value

            return setting[0]
        elif self.setting_type == SettingType.LIST:
            setting = c.execute(
                select(usl_table.c.value).where(
                    (usl_table.c.uid == str(member))
                    & (usl_table.c.name == self.name)
                )
            ).fetchall()

            if len(setting) == 0:
                return []

            return [i[0] for i in setting]
        else:
            raise ValueError(f"Variable type {self.setting_type} is invalid")

    def set(self, c: Connection, member: Member, value: str):
        if self.setting_type != SettingType.NORMAL:
            raise InvalidOperation(
                f"Cannot operate on type {self.setting_type}, it must be {SettingType.NORMAL}"
            )

        setting = c.execute(
            select(us_table).where(
                (us_table.c.uid == str(member.id)) & (us_table.c.name == self.name)
            )
        ).fetchone()

        if setting is None:
            c.execute(
                insert(us_table).values(
                    uid=str(member.id), name=self.name, value=value
                )
            )
        else:
            c.execute(
                update(us_table)
                .values(value=value)
                .where(
                    (us_table.c.uid == str(member.id)) & (us_table.c.name == self.name)
                )
            )

    def add_to_list(
        self, c: Connection, member: Member, value: str, silent: bool = False
    ):
        if self.setting_type != SettingType.LIST:
            raise InvalidOperation(
                f"Cannot operate on type {self.setting_type}, it must be {SettingType.LIST}"
            )

        a = c.execute(
            select(usl_table.c.value).where(
                (usl_table.c.uid == str(member.id))
                & (usl_table.c.name == self.name)
                & (usl_table.c.value == value)
            )
        ).fetchone()

        if a is not None:
            if silent:
                return

            raise ValueError(f"Value {value} is already in list {self.name}")

        c.execute(
            insert(usl_table).values(
                uid=str(member.guild.id), name=self.name, value=value
            )
        )

    def remove_from_list(
        self, c: Connection, member: Member, value: str, silent: bool = False
    ):
        if self.setting_type != SettingType.LIST:
            raise InvalidOperation(
                f"Cannot operate on type {self.setting_type}, it must be {SettingType.LIST}"
            )

        a = c.execute(
            select(usl_table.c.value).where(
                (usl_table.c.uid == str(member.id))
                & (usl_table.c.name == self.name)
                & (usl_table.c.value == value)
            )
        ).fetchone()

        if a is None:
            if silent:
                return

            raise ValueError(f"Value {value} not found in list {self.name}")

        c.execute(
            delete(usl_table).where(
                (usl_table.c.uid == str(member.id))
                & (usl_table.c.name == self.name)
                & (usl_table.c.value == value)
            )
        )

    def is_in_list(self, c: Connection, member: Member, value: str) -> bool:
        a = c.execute(
            select(usl_table.c.value).where(
                (usl_table.c.uid == str(member.id))
                & (usl_table.c.name == self.name)
                & (usl_table.c.value == value)
            )
        ).fetchone()

        return a is not None

    def clear_list(self, c: Connection, member: Member):
        c.execute(
            delete(usl_table.c.value).where(
                (usl_table.c.uid == str(member.id)) & (usl_table.c.name == self.name)
            )
        )
