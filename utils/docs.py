from utils.server_settings import SettingType


class DocsCommandParameter:
    def __init__(
        self,
        name: str,
        description: str,
        *,
        parameter_type: str = "str",
        optional: bool = False,
    ):
        self.name = name
        self.description = description
        self.parameter_type = (parameter_type,)
        self.optional = optional

    def __str__(self):
        return (
            ("`[" if self.optional else "`<")
            + self.name
            + ("]`" if self.optional else ">`")
            + " - "
            + self.description
        )


class DocsCommand:
    def __init__(
        self,
        command: str,
        description: str,
        *,
        parameters: list[DocsCommandParameter] = [],
    ):
        self.command = command
        self.description = description
        self.parameters = parameters

    def __str__(self):
        a = "- `/" + self.command + "` - " + self.description + "\n"

        if len(self.parameters) > 0:
            a += "\t- **Parameters**:\n"
            for i in self.parameters:
                a += "\t\t- " + str(i) + "\n"

        return a


class DocsSetting:
    def __init__(
        self,
        name: str,
        *,
        setting_type: SettingType,
        description: str = "No description for this setting",
        set_description: str = "Set the setting to the value",
        add_description: str = "Add the value to the list",
        remove_description: str = "Remove the value from the list",
    ):
        self.name = name
        self.setting_type = setting_type
        self.description = description

        if setting_type == SettingType.NORMAL:
            self.set_description = set_description
        elif setting_type == SettingType.LIST:
            self.add_description = add_description
            self.remove_description = remove_description

    def __str__(self):
        if self.setting_type == SettingType.NORMAL:
            return (
                f"- Setting `{self.name}` - {self.description}\n"
                + f"\t- **Set the setting** - `/settings set_setting name:{self.name} value:<your value>` {self.set_description}"
            )
        elif self.setting_type == SettingType.LIST:
            return (
                f"- Setting `{self.name}` - {self.description}\n"
                + f"\t- **Add to list** - `/settings add_to_list name:{self.name} value:<your value>` - {self.add_description}\n"
                + f"\t- **Remove from list** - `/settings remove_from_list name:{self.name} value:<your value>` - {self.remove_description}"
            )

        return f"Undefined description for setting {self.name}"


class Docs:
    def __init__(
        self,
        name: str,
        *,
        description: str = "No description set for this command",
        commands: list[DocsCommand] = None,
        settings: list[DocsSetting] = None,
    ):
        if commands is None:
            commands = []
        if settings is None:
            settings = []
        self.name = name
        self.description = description
        self.commands = commands
        self.settings = settings

    def __str__(self):
        a = "# " + self.name + "\n\n" + self.description + "\n\n"

        if len(self.commands) > 0:
            a += "## Commands:\n\n"
            for i in self.commands:
                a += str(i) + "\n"

        if len(self.settings) > 0:
            a += "## Settings:\n\n"
            for i in self.settings:
                a += str(i) + "\n\n"

        return a
