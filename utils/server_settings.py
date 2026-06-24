from decimal import InvalidOperation
from enum import Enum
from typing import Callable

from discord import AutocompleteContext, Member
from sqlalchemy import Connection, delete, insert, select, update

from database import server_settings, server_settings_list
from logger import akabot_logger
from utils.conversion import convert_role, convert_text_channel, convert_voice_channel


class SettingType(Enum):
    NORMAL = 1
    LIST = 2


class ServerSetting:
    def __init__(
        self,
        name: str,
        *,
        setting_type: SettingType = SettingType.NORMAL,
        default: str | None = None
    ):
        self.name = name
        self.setting_type = setting_type

        if self.setting_type == SettingType.NORMAL:
            self.default_value = default
        elif self.setting_type == SettingType.LIST:
            self.default_value = []

    def default(self) -> list | str:
        return self.default_value

    def get(self, c: Connection, guild_id: int) -> str | list[str]:
        if self.setting_type == SettingType.NORMAL:
            setting = c.execute(
                select(server_settings.c.value).where(
                    (server_settings.c.uid == str(guild_id))
                    & (server_settings.c.name == self.name)
                )
            ).fetchone()

            if setting is None:
                return self.default_value

            return setting[0]
        elif self.setting_type == SettingType.LIST:
            setting = c.execute(
                select(server_settings_list.c.value).where(
                    (server_settings_list.c.uid == str(guild_id))
                    & (server_settings_list.c.name == self.name)
                )
            ).fetchall()

            if len(setting) == 0:
                return []

            return [i[0] for i in setting]
        else:
            raise ValueError(f"Variable type {self.setting_type} is invalid")

    def set(self, c: Connection, guild_id: int, value: str):
        if self.setting_type != SettingType.NORMAL:
            raise InvalidOperation(
                f"Cannot operate on type {self.setting_type}, it must be {SettingType.NORMAL}"
            )

        setting = c.execute(
            select(server_settings.c.value).where(
                (server_settings.c.uid == str(guild_id))
                & (server_settings.c.name == self.name)
            )
        ).fetchone()

        if setting is None:
            c.execute(
                insert(server_settings).values(
                    uid=str(guild_id), name=self.name, value=value
                )
            )
        else:
            c.execute(
                update(server_settings)
                .values(value=value)
                .where(
                    (server_settings.c.uid == str(guild_id))
                    & (server_settings.c.name == self.name)
                )
            )

    def add_to_list(
            self, c: Connection, guild_id: int, value: str, silent: bool = False
    ):
        if self.setting_type != SettingType.LIST:
            raise InvalidOperation(
                f"Cannot operate on type {self.setting_type}, it must be {SettingType.LIST}"
            )

        a = c.execute(
            select(server_settings_list.c.value).where(
                (server_settings_list.c.uid == str(guild_id))
                & (server_settings_list.c.name == self.name)
                & (server_settings_list.c.value == value)
            )
        ).fetchone()

        if a is not None:
            if silent:
                return

            raise ValueError(f"Value {value} is already in list {self.name}")

        c.execute(
            insert(server_settings_list).values(
                uid=str(guild_id), name=self.name, value=value
            )
        )

    def remove_from_list(
            self, c: Connection, guild_id: int, value: str, silent: bool = False
    ):
        if self.setting_type != SettingType.LIST:
            raise InvalidOperation(
                f"Cannot operate on type {self.setting_type}, it must be {SettingType.LIST}"
            )

        a = c.execute(
            select(server_settings_list.c.value).where(
                (server_settings_list.c.uid == str(guild_id))
                & (server_settings_list.c.name == self.name)
                & (server_settings_list.c.value == value)
            )
        ).fetchone()

        if a is None:
            if silent:
                return

            raise ValueError(f"Value {value} not found in list {self.name}")

        c.execute(
            delete(server_settings_list).where(
                (server_settings_list.c.uid == str(guild_id))
                & (server_settings_list.c.name == self.name)
                & (server_settings_list.c.value == value)
            )
        )

    def is_in_list(self, c: Connection, guild_id: int, value: str) -> bool:
        a = c.execute(
            select(server_settings_list.c.value).where(
                (server_settings_list.c.uid == str(guild_id))
                & (server_settings_list.c.name == self.name)
                & (server_settings_list.c.value == value)
            )
        ).fetchone()

        return a is not None

    def clear_list(self, c: Connection, member: Member):
        c.execute(
            delete(server_settings_list.c.value).where(
                (server_settings_list.c.uid == str(member.guild.id))
                & (server_settings_list.c.name == self.name)
            )
        )


def setting_choice(*choices: str):
    def processor(c: Connection, m: Member, v: str) -> tuple[bool, str]:
        if v.strip() in choices:
            return True, v

        return False, f"Invalid choice \"{v}\", pick one from {', '.join(choices)}."

    return processor
