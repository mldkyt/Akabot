from discord import Guild, Role


def convert_role(guild: Guild, value: str, index: int = 0) -> Role | None:
    # ID
    if value.isnumeric():
        return guild.get_role(int(value))

    # Try and find it by name startswith
    by_name = [i for i in guild.roles if i.name.startswith(value)]
    if len(by_name) > index:
        return by_name[index]

    # Try and find it by name contains
    by_name = [i for i in guild.roles if value in i.name]
    if len(by_name) > index:
        return by_name[index]

    return None
