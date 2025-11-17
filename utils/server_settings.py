from decimal import InvalidOperation
from enum import Enum
from typing import Callable

from discord import Member, AutocompleteContext, Guild
from sqlalchemy import Connection, select, insert, update, delete

from database import server_settings, server_settings_list
from utils.conversion import convert_text_channel, convert_role


class SettingType(Enum):
    NORMAL = 1
    LIST = 2

class ServerSetting:
    def __init__(self, name: str, *, setting_type: SettingType = SettingType.NORMAL,
                 normal_validator: Callable[[Connection, Member, str], tuple[bool, str]] | None = None, list_add_validator: Callable[[Connection, Member, str], tuple[bool, str]] | None = None, list_remove_validator: Callable[[Connection, Member, str], tuple[bool, str]] | None = None,
                 normal_transformer: Callable[[Connection, Member, str], str] | None = None, list_add_transformer: Callable[[Connection, Member, str], str] | None = None, list_remove_transformer: Callable[[Connection, Member, str], str] | None = None,
                 default: str | None = None, normal_response: Callable[[Connection, Member, str], str] | None = None, list_add_response: Callable[[Connection, Member, str], str] | None = None, list_remove_response: Callable[[Connection, Member, str], str] | None = None,
                 normal_view: Callable[[Connection, Member, str], str] | None = None, list_view: Callable[[Connection, Member, list[str]], str] | None = None):
        self.name = name

        self.setting_type = setting_type

        if self.setting_type == SettingType.NORMAL:
            self.default_value = default
            self.normal_validator = normal_validator
            self.normal_transformer = normal_transformer
            self.normal_response = normal_response
            self.normal_view = normal_view
        elif self.setting_type == SettingType.LIST:
            self.default_value = []
            self.list_add_validator = list_add_validator
            self.list_add_transformer = list_add_transformer
            self.list_add_response = list_add_response
            self.list_remove_validator = list_remove_validator
            self.list_remove_transformer = list_remove_transformer
            self.list_remove_response = list_remove_response
            self.list_view = list_view

    def validate_add(self, c: Connection, member: Member, value: str) -> tuple[bool, str]:
        if self.setting_type == SettingType.NORMAL:
            if self.normal_validator is None:
                return True, ""

            return self.normal_validator(c, member, value)
        elif self.setting_type == SettingType.LIST:
            if self.list_add_validator is None:
                return True, ""

            return self.list_add_validator(c, member, value)

        raise ValueError(f"Invalid setting_type {self.setting_type} for validate_add")

    def validate_remove(self, c: Connection, member: Member, value: str) -> tuple[bool, str]:
        if self.setting_type == SettingType.LIST:
            if self.list_remove_validator is None:
                return True, ""

            return self.list_remove_validator(c, member, value)

        raise ValueError(f"Invalid setting_type {self.setting_type} for validate_remove")

    def transform_add(self, c: Connection, member: Member, value: str) -> str:
        if self.setting_type == SettingType.NORMAL:
            if self.normal_transformer is None:
                return value

            return self.normal_transformer(c, member, value)
        elif self.setting_type == SettingType.LIST:
            if self.list_add_transformer is None:
                return value

            return self.list_add_transformer(c, member, value)

        raise ValueError(f"Invalid setting_type {self.setting_type} for transform_add")

    def transform_remove(self, c: Connection, member: Member, value: str) -> str:
        if self.setting_type == SettingType.LIST:
            if self.list_remove_transformer is None:
                return value

            return self.list_remove_transformer(c, member, value)

        raise ValueError(f"Invalid setting_type {self.setting_type} for transform_remove")

    def respond_add(self, c: Connection, member: Member, value: str) -> str:
        value = self.transform_add(c, member, value)

        if self.setting_type == SettingType.NORMAL:
            if self.normal_response is None:
                return f"Set {self.name} to {value}"

            return self.normal_response(c, member, value)
        elif self.setting_type == SettingType.LIST:
            if self.list_add_response is None:
                return f"Added {value} to list {self.name}"

            return self.list_add_response(c, member, value)

        raise ValueError(f"Invalid setting_type {self.setting_type} for respond_add")

    def respond_remove(self, c: Connection, member: Member, value: str) -> str:
        value = self.transform_remove(c, member, value)

        if self.setting_type == SettingType.LIST:
            if self.list_remove_response is None:
                return f"Removed {value} from list {self.name}"

            return self.list_remove_response(c, member, value)

        raise ValueError(f"Invalid setting_type {self.setting_type} for respond_remove")

    def default(self) -> list | str:
        return self.default_value

    def get(self, c: Connection, member: Member) -> str | list[str]:
        if self.setting_type == SettingType.NORMAL:

            setting = c.execute(
                select(server_settings.c.value)
                .where((server_settings.c.uid == str(member.guild.id)) & (server_settings.c.name == self.name))
            ).fetchone()

            if setting is None:
                return self.default_value

            return setting[0]
        elif self.setting_type == SettingType.LIST:
            setting = c.execute(
                select(server_settings_list.c.value)
                .where((server_settings_list.c.uid == str(member.guild.id)) & (server_settings_list.c.name == self.name))
            ).fetchall()

            if len(setting) == 0:
                return []

            return [i[0] for i in setting]
        else:
            raise ValueError(f"Variable type {self.setting_type} is invalid")

    def get_direct(self, c: Connection, g: Guild) -> str | list[str]:
        if self.setting_type == SettingType.NORMAL:

            setting = c.execute(
                select(server_settings.c.value)
                .where((server_settings.c.uid == str(g.id)) & (server_settings.c.name == self.name))
            ).fetchone()

            if setting is None:
                return self.default_value

            return setting[0]
        elif self.setting_type == SettingType.LIST:
            setting = c.execute(
                select(server_settings_list.c.value)
                .where((server_settings_list.c.uid == str(g.id)) & (server_settings_list.c.name == self.name))
            ).fetchall()

            if len(setting) == 0:
                return []

            return [i[0] for i in setting]
        else:
            raise ValueError(f"Variable type {self.setting_type} is invalid")

    def get_formatted(self, c: Connection, m: Member):
        if self.setting_type == SettingType.NORMAL:
            val = self.get(c, m)
            if self.normal_view is not None:
                return self.normal_view(c, m, val)
            return f"Setting `{self.name}` has value `{val}`"
        elif self.setting_type == SettingType.LIST:
            val = self.get(c, m)
            if self.list_view is not None:
                return self.list_view(c, m, val)
            return f"Setting `{self.name}` has value `{', '.join(val)}`"
        else:
            raise ValueError(f"Variable type {self.setting_type} is invalid")

    def set(self, c: Connection, member: Member, value: str):
        if self.setting_type != SettingType.NORMAL:
            raise InvalidOperation(f"Cannot operate on type {self.setting_type}, it must be {SettingType.NORMAL}")

        ok, err = self.validate_add(c, member, value)
        if not ok:
            raise ValueError(err)

        value = self.transform_add(c, member, value)

        setting = c.execute(
            select(server_settings.c.value)
            .where((server_settings.c.uid == str(member.guild.id)) & (server_settings.c.name == self.name))
        ).fetchone()

        if setting is None:
            c.execute(
                insert(server_settings)
                .values(uid=str(member.guild.id), name=self.name, value=value)
            )
        else:
            c.execute(
                update(server_settings)
                .values(value=value)
                .where((server_settings.c.uid == str(member.guild.id)) & (server_settings.c.name == self.name))
            )

    def add_to_list(self, c: Connection, member: Member, value: str, silent: bool = False):
        if self.setting_type != SettingType.LIST:
            raise InvalidOperation(f"Cannot operate on type {self.setting_type}, it must be {SettingType.LIST}")

        ok, err = self.validate_add(c, member, value)
        if not ok:
            raise ValueError(err)

        value = self.transform_add(c, member, value)

        a = c.execute(
            select(server_settings_list.c.value)
            .where((server_settings_list.c.uid == str(member.guild.id)) & (server_settings_list.c.name == self.name) & (
                        server_settings_list.c.value == value))
        ).fetchone()

        if a is not None:
            if silent:
                return

            raise ValueError(f"Value {value} is already in list {self.name}")

        c.execute(
            insert(server_settings_list)
            .values(uid=str(member.guild.id), name=self.name, value=value)
        )

    def remove_from_list(self, c: Connection, member: Member, value: str, silent: bool = False):
        if self.setting_type != SettingType.LIST:
            raise InvalidOperation(f"Cannot operate on type {self.setting_type}, it must be {SettingType.LIST}")

        ok, err = self.validate_remove(c, member, value)
        if not ok:
            raise ValueError(err)

        value = self.transform_remove(c, member, value)

        a = c.execute(
            select(server_settings_list.c.value)
            .where((server_settings_list.c.uid == str(member.guild.id)) & (server_settings_list.c.name == self.name) & (
                        server_settings_list.c.value == value))
        ).fetchone()

        if a is None:
            if silent:
                return

            raise ValueError(f"Value {value} not found in list {self.name}")

        c.execute(
            delete(server_settings_list)
            .where((server_settings_list.c.uid == str(member.guild.id)) & (server_settings_list.c.name == self.name) & (
                        server_settings_list.c.value == value))
        )

    def is_in_list(self, c: Connection, member: Member, value: str) -> bool:
        a = c.execute(
            select(server_settings_list.c.value)
            .where((server_settings_list.c.uid == str(member.guild.id)) & (server_settings_list.c.name == self.name) & (
                    server_settings_list.c.value == value))
        ).fetchone()

        return a is not None

    def clear_list(self, c: Connection, member: Member):
        c.execute(
            delete(server_settings_list.c.value)
            .where((server_settings_list.c.uid == str(member.guild.id)) & (server_settings_list.c.name == self.name))
        )

class ServerSettings:
    def __init__(self):
        self.registered_settings: list[ServerSetting] = []

    def add_setting(self, setting: ServerSetting):
        self.registered_settings.append(setting)

    def add_settings(self, *setting: ServerSetting):
        self.registered_settings.extend(setting)

    def get_settings(self) -> list[ServerSetting]:
        return self.registered_settings

    def get_setting(self, name: str) -> ServerSetting | None:
        for i in self.registered_settings:
            if i.name == name:
                return i

        return None

    def list_server_settings_pretty(self, c: Connection, member: Member) -> list[tuple[str, str]]:
        sets = []

        for i in self.registered_settings:
            if i.setting_type == SettingType.NORMAL:
                sets.append(i.get_formatted(c, member))
            elif i.setting_type == SettingType.LIST:
                sets.append(i.get_formatted(c, member))
            # Add any other setting types here in the future

        return sets

settings = ServerSettings()


# noinspection PyUnusedLocal
def setting_is_number(c: Connection, member: Member, value: str):
    if not value.isnumeric():
        return False, f"{value} is not a number"

    return True, ""

BOOLEAN_VALUES = ["true", "yes", "y", "1", "Y", "Yes", "On", "ON", "on",
                  "false", "no", "n", "0", "N", "No", "Off", "OFF", "off"]

# noinspection PyUnusedLocal
def setting_is_boolean(c: Connection, member: Member, value: str):
    if value not in BOOLEAN_VALUES:
        return False, f"{value} is not a yes/no"

    return True, ""

# noinspection PyUnusedLocal
def setting_to_boolean(c: Connection, member: Member, value: str) -> str:
    if value in ["true", "yes", "y", "1", "Y", "Yes", "On", "ON", "on"]:
        return "true"
    else:
        return "false"

# noinspection PyUnusedLocal
def setting_is_channel(c: Connection, member: Member, value: str) -> tuple[bool, str]:
    s = value.split(",")
    if len(s) == 2 and s[1].isnumeric():
        chat_convert = convert_text_channel(member.guild, s[0], int(s[1]))
    else:
        chat_convert = convert_text_channel(member.guild, value)

    if chat_convert is None:
        return False, "Invalid channel"
    else:
        return True, ""

# noinspection PyUnusedLocal
def setting_to_channel(c: Connection, member: Member, value: str) -> str:
    s = value.split(",")
    if len(s) == 2 and s[1].isnumeric():
        chat_convert = convert_text_channel(member.guild, s[0], int(s[1]))
    else:
        chat_convert = convert_text_channel(member.guild, value)

    if chat_convert is None:
        raise ValueError("Value should not be null! This should have been caught by setting_is_channel")

    return str(chat_convert.id)

# noinspection PyUnusedLocal
def setting_is_role(c: Connection, member: Member, value: str) -> tuple[bool, str]:
    s = value.split(",")
    if len(s) == 2 and s[1].isnumeric():
        role_convert = convert_role(member.guild, s[0], int(s[1]))
    else:
        role_convert = convert_role(member.guild, value)

    if role_convert is None:
        return False, "Invalid channel"
    else:
        return True, ""

# noinspection PyUnusedLocal
def setting_to_role(c: Connection, member: Member, value: str) -> str:
    s = value.split(",")
    if len(s) == 2 and s[1].isnumeric():
        role_convert = convert_role(member.guild, s[0], int(s[1]))
    else:
        role_convert = convert_role(member.guild, value)

    if role_convert is None:
        raise ValueError("Value should not be null! This should have been caught by setting_is_channel")

    return str(role_convert.id)


def setting_simple_string(fmt: str):
    def formatter(c: Connection, m: Member, v: str) -> str:
        return fmt.replace("%s", v)

    return formatter


def setting_simple_list_string(fmt: str, sep: str, empty: str):
    def formatter(c: Connection, m: Member, v: list[str]) -> str:
        if len(v) == 0:
            return empty
        return fmt.replace("%s", sep.join(v))

    return formatter


def setting_simple_string_boolean(fmt: str, truthy: str, falsey: str):
    def formatter(c: Connection, m: Member, v: str) -> str:
        if v == "true":
            return fmt.replace("%s", truthy)
        else:
            return fmt.replace("%s", falsey)

    return formatter


def setting_name_autocomplete(ctx: AutocompleteContext) -> list[str]:
    setting = ctx.options["name"]

    options = [i.name for i in settings.get_settings() if i.name.startswith(setting) and i.setting_type == SettingType.NORMAL]
    options = options[:10]

    return options

def setting_name_list_autocomplete(ctx: AutocompleteContext) -> list[str]:
    setting = ctx.options["name"]

    options = [i.name for i in settings.get_settings() if i.name.startswith(setting) and i.setting_type == SettingType.LIST]
    options = options[:10]

    return options
