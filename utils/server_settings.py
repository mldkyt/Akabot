from idlelib.tree import wheel_event
from typing import Callable

import discord
from sqlalchemy import Connection, select, insert, update

from database import server_settings

class ServerSettings:
    def __init__(self):
        self.registered_settings: list[str] = []
        self.registered_validators: list[tuple[str, Callable[[str], bool]]] = []
        self.registered_transformers: list[tuple[str, Callable[[str], str]]] = []
        self.registered_defaults: list[tuple[str, str]] = []

    def add_setting(self, name: str):
        self.registered_settings.append(name)

    def register_settings(self, *settings_to_add: str):
        for i in settings_to_add:
            self.add_setting(i)

    def get_settings(self) -> list[str]:
        return self.registered_settings

    def register_validator(self, name: str, proc: Callable[[str], bool]):
        self.registered_validators.append(
            (name, proc)
        )

    def get_registered_validators(self, name: str) -> list[Callable[[str], bool]]:
        return [i[1] for i in self.registered_validators if i[0] == name]

    def register_transformer(self, name: str, proc: Callable[[str], str]):
        self.registered_transformers.append(
            (name, proc)
        )

    def get_registered_transformers(self, name: str) -> list[Callable[[str], str]]:
        return [i[1] for i in self.registered_transformers if i[0] == name]

    def register_default(self, name: str, default: str):
        self.registered_defaults.append((name, default))

    def register_defaults(self, *defaults: tuple[str, str]):
        self.registered_defaults.extend(defaults)

    def get_default(self, name: str) -> str | None:
        default = [i for i in self.registered_defaults if i[0] == name]
        if len(default) == 0:
            return None

        return default[0][1]


def setting_is_number(value: str):
    return value.isnumeric()

def setting_is_boolean(value: str):
    return value in ["true", "yes", "y", "1", "Y", "Yes", "On", "ON", "on",
                     "false", "no", "n", "0", "N", "No", "Off", "OFF", "off"]

def validate_setting(name: str, new_value: str) -> bool:
    validators = settings.get_registered_validators(name)
    for i in validators:
        if not i(new_value):
            return False

    return True

def transform_setting(name: str, new_value: str) -> str:
    validators = settings.get_registered_transformers(name)
    for i in validators:
        new_value = i(new_value)

    return new_value

def setting_to_boolean(value: str) -> str:
    if value in ["true", "yes", "y", "1", "Y", "Yes", "On", "ON", "on"]:
        return "true"
    else:
        return "false"

def get_server_setting(c: Connection, uid: int, name: str):
    setting = c.execute(
        select(server_settings.c.value)
            .where((server_settings.c.uid == uid) & (server_settings.c.name == name))
    ).fetchone()

    if setting is None:
        return settings.get_default(name)

    return setting[0]

settings = ServerSettings()

def set_server_setting(c: Connection, uid: int, name: str, value: str):
    if not validate_setting(name, value):
        raise ValueError(f"Invalid value {value} for setting {name}")

    value = transform_setting(name, value)

    setting = c.execute(
        select(server_settings.c.value)
            .where((server_settings.c.uid == uid) & (server_settings.c.name == name))
    ).fetchone()

    if setting is None:
        c.execute(
            insert(server_settings)
                .values(uid=uid, name=name, value=value)
        )
    else:
        c.execute(
            update(server_settings)
                .values(value=value)
                .where((server_settings.c.uid == uid) & (server_settings.c.name == name))
        )

def list_server_settings(c: Connection, uid: int) -> list[tuple[str, str]]:
    sets = []

    for i in settings.registered_settings:
        sets.append((i, get_server_setting(c, uid, i)))

    return [(i[0], i[1]) for i in sets]

def setting_name_autocomplete(ctx: discord.AutocompleteContext) -> list[str]:
    setting = ctx.options["name"]

    options = [i for i in settings.get_settings() if i.startswith(setting)]
    options = options[:10]

    return options
