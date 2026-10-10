from utils.server_settings import KV


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


class Docs:
    def __init__(
        self,
        name: str,
        *,
        description: str = "No description set for this command",
        commands: list[DocsCommand] = None,
            settings: list[KV] = None,
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
