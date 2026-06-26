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
            normal_processor: Callable[[Connection, Member, str], tuple[bool, str]] | None = None,
            list_add_processor: Callable[[Connection, Member, str], tuple[bool, str]] | None = None,
            list_remove_processor: Callable[[Connection, Member, str], tuple[bool, str]] | None = None,
        default: str | None = None,
        normal_response: Callable[[Connection, Member, str], str] | None = None,
        list_add_response: Callable[[Connection, Member, str], str] | None = None,
        list_remove_response: Callable[[Connection, Member, str], str] | None = None,
        normal_view: Callable[[Connection, Member, str], str] | None = None,
        list_view: Callable[[Connection, Member, list[str]], str] | None = None,
    ):
        self.name = name

        self.setting_type = setting_type

        if self.setting_type == SettingType.NORMAL:
            self.default_value = default
            self.normal_transformer = normal_processor
            self.normal_response = normal_response
            self.normal_view = normal_view
        elif self.setting_type == SettingType.LIST:
            self.default_value = []
            self.list_add_transformer = list_add_processor
            self.list_add_response = list_add_response
            self.list_remove_transformer = list_remove_processor
            self.list_remove_response = list_remove_response
            self.list_view = list_view

    def process_add(self, c: Connection, member: Member, value: str) -> tuple[bool, str]:
        if self.setting_type == SettingType.NORMAL:
            if self.normal_transformer is None:
                return True, value

            return self.normal_transformer(c, member, value)
        elif self.setting_type == SettingType.LIST:
            if self.list_add_transformer is None:
                return True, value

            return self.list_add_transformer(c, member, value)

        raise ValueError(f"Invalid setting_type {self.setting_type} for transform_add")

    def process_remove(self, c: Connection, member: Member, value: str) -> tuple[bool, str]:
        if self.setting_type == SettingType.LIST:
            if self.list_remove_transformer is None:
                return True, value

            return self.list_remove_transformer(c, member, value)

        raise ValueError(
            f"Invalid setting_type {self.setting_type} for transform_remove"
        )

    def respond_add(self, c: Connection, member: Member, value: str) -> str:
        ok, value = self.process_add(c, member, value)

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
        ok, value = self.process_remove(c, member, value)

        if self.setting_type == SettingType.LIST:
            if self.list_remove_response is None:
                return f"Removed {value} from list {self.name}"

            return self.list_remove_response(c, member, value)

        raise ValueError(f"Invalid setting_type {self.setting_type} for respond_remove")

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

    def get_formatted(self, c: Connection, m: Member):
        if self.setting_type == SettingType.NORMAL:
            val = self.get(c, m.id)
            if self.normal_view is not None:
                return self.normal_view(c, m, val)
            return f"Setting `{self.name}` has value `{val}`"
        elif self.setting_type == SettingType.LIST:
            val = self.get(c, m.id)
            if self.list_view is not None:
                return self.list_view(c, m, val)
            return f"Setting `{self.name}` has value `{', '.join(val)}`"
        else:
            raise ValueError(f"Variable type {self.setting_type} is invalid")

    def set(self, c: Connection, member: Member, value: str):
        if self.setting_type != SettingType.NORMAL:
            raise InvalidOperation(
                f"Cannot operate on type {self.setting_type}, it must be {SettingType.NORMAL}"
            )

        ok, value = self.process_add(c, member, value)
        if not ok:
            raise ValueError(value)

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

        ok, value = self.process_add(c, member, value)
        if not ok:
            raise ValueError(value)

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

        ok, value = self.process_remove(c, member, value)
        if not ok:
            raise ValueError(value)

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


class UserSettings:
    def __init__(self):
        self.registered_settings: list[UserSetting] = []

    def add_setting(self, setting: UserSetting):
        self.registered_settings.append(setting)

    def add_settings(self, *setting: UserSetting):
        self.registered_settings.extend(setting)

    def get_settings(self) -> list[UserSetting]:
        return self.registered_settings

    def get_setting(self, name: str) -> UserSetting | None:
        for i in self.registered_settings:
            if i.name == name:
                return i

        return None

    def list_user_settings_pretty(
        self, c: Connection, member: Member
    ) -> list[tuple[str, str]]:
        sets = []

        for i in self.registered_settings:
            if i.setting_type == SettingType.NORMAL:
                sets.append(i.get_formatted(c, member))
            elif i.setting_type == SettingType.LIST:
                sets.append(i.get_formatted(c, member))
            # Add any other setting types here in the future

        return sets


user_settings = UserSettings()


def user_setting_name_autocomplete(ctx: AutocompleteContext) -> list[str]:
    setting = ctx.options["name"]

    options = [
        i.name
        for i in user_settings.get_settings()
        if i.name.startswith(setting) and i.setting_type == SettingType.NORMAL
    ]
    options = options[:10]

    return options


def user_setting_name_list_autocomplete(ctx: AutocompleteContext) -> list[str]:
    setting = ctx.options["name"]

    options = [
        i.name
        for i in user_settings.get_settings()
        if i.name.startswith(setting) and i.setting_type == SettingType.LIST
    ]
    options = options[:10]

    return options
