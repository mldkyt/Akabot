from discord import Cog, Interaction, InteractionType, Role, ApplicationContext, option, ButtonStyle, SlashCommandGroup, \
    Bot, Message, Permissions, NotFound
from discord.ext import commands as commands_ext
from discord.ui import Button, View, ActionRow

from logger import nekona_logger


def get_roles(msg: Message):
    roles = []

    if msg.guild is None:
        return []

    for i in msg.components:
        if not isinstance(i, ActionRow):
            continue

        for j in i.children:
            if not isinstance(j, Button):
                continue

            split = j.custom_id.split('-')
            if len(split) != 2:
                continue

            if split[0] not in ['rrn', 'rra', 'rrr', 'rrs']:
                continue

            if not split[1].isdigit():
                continue

            role = msg.guild.get_role(int(split[1]))
            if role is None:
                continue

            roles.append(role)

    return roles


class ReactionRoles(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()

        self.bot = bot

    reaction_roles_subcommand = SlashCommandGroup(name="reaction_roles", description="Create a reaction role",
                                                  default_member_permissions=Permissions(manage_roles=True))

    def create_view(self, role_type: str, roles: list[Role]) -> View:
        view = View()
        for role in roles:
            if role is None:
                continue

            view.add_item(
                Button(style=ButtonStyle.primary, label=role.name, custom_id=f"rr{role_type}-{role.id}"))

        return view

    @reaction_roles_subcommand.command(name="create", description="Create a reaction role")
    @option(name="role_type", description="Type of reaction role",
            choices=["normal", "add only", "remove only", "single"])
    @commands_ext.guild_only()
    @commands_ext.bot_has_permissions(send_messages=True)
    async def create_reaction_role(self, interaction: ApplicationContext, role_type: str, message: str,
                                   role_1: Role, role_2: Role = None, role_3: Role = None,
                                   role_4: Role = None, role_5: Role = None,
                                   role_6: Role = None, role_7: Role = None,
                                   role_8: Role = None, role_9: Role = None,
                                   role_10: Role = None) -> None:
        try:
            if role_type == "single":
                role_type = "s"
            elif role_type == "add only":
                role_type = "a"
            elif role_type == "remove only":
                role_type = "r"
            else:
                role_type = "n"

            roles = [role_1, role_2, role_3, role_4, role_5, role_6, role_7, role_8, role_9, role_10]
            view = self.create_view(role_type, roles)

            await interaction.channel.send(content=message, view=view)
            await interaction.response.send_message("Reaction role has been created!",
                                                    ephemeral=True)
        except Exception as e:
            nekona_logger.exception("An error occured:")
            await interaction.response.send_message("An error occured", ephemeral=True)

    @reaction_roles_subcommand.command(name="edit", description="Edit a reaction role")
    @option(name="message_id", description="Message ID to edit")
    @option(name="role_type", description="Type of reaction role",
            choices=["normal", "add only", "remove only", "single"])
    @commands_ext.guild_only()
    @commands_ext.bot_has_permissions(send_messages=True)
    async def edit_reaction_role(self, interaction: ApplicationContext, message_id: str, role_type: str,
                                 role_1: Role, role_2: Role = None, role_3: Role = None,
                                 role_4: Role = None, role_5: Role = None, role_6: Role = None,
                                 role_7: Role = None, role_8: Role = None, role_9: Role = None,
                                 role_10: Role = None, content: str = None) -> None:
        try:
            if not message_id.isdigit():
                await interaction.response.send_message("Message ID must be a number!",
                                                        ephemeral=True)
                return

            try:
                message = await interaction.channel.fetch_message(int(message_id))
            except NotFound:
                await interaction.response.send_message("Message not found", ephemeral=True)
                return

            if message.author.id != self.bot.user.id:
                await interaction.response.send_message("The message must be sent by me", ephemeral=True)
                return

            if role_type == "single":
                role_type = "s"
            elif role_type == "add only":
                role_type = "a"
            elif role_type == "remove only":
                role_type = "r"
            else:
                role_type = "n"

            roles = [role_1, role_2, role_3, role_4, role_5, role_6, role_7, role_8, role_9, role_10]
            view = self.create_view(role_type, roles)

            if not content:
                await message.edit(view=view)
            else:
                await message.edit(content=content, view=view)

            await interaction.response.send_message("Reaction role has been edited!",
                                                    ephemeral=True)
        except Exception as e:
            nekona_logger.exception("An error occured:")
            await interaction.response.send_message("An error occured", ephemeral=True)

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction) -> None:
        try:
            if interaction.type != InteractionType.component:
                return
            split = interaction.custom_id.split('-')
            if len(split) != 2:
                return

            if split[0] not in ['rrn', 'rra', 'rrr', 'rrs']:
                return

            if not split[1].isdigit():
                return

            if not interaction.guild.me.guild_permissions.manage_roles:
                await interaction.response.send_message("I do not have permissions to manage roles!", ephemeral=True)
                return

            role = interaction.guild.get_role(int(split[1]))
            if role is None:
                return

            if role.position >= interaction.guild.me.top_role.position:
                await interaction.response.send_message("I cannot assign this role!", ephemeral=True)
                return

            if split[0] == "rrn":
                if role in interaction.user.roles:
                    await interaction.response.send_message(f"Role {role.mention} has been removed from you!",
                                                            ephemeral=True)
                    await interaction.user.remove_roles(role, reason="Reaction role")
                    return
                if role not in interaction.user.roles:
                    await interaction.response.send_message(f"Role {role.mention} has been added to you!",
                                                            ephemeral=True)
                    await interaction.user.add_roles(role, reason="Reaction role")
                    return

            if split[0] == "rra":
                if role in interaction.user.roles:
                    await interaction.response.send_message("You already have this role!", ephemeral=True)
                    return
                if role not in interaction.user.roles:
                    await interaction.response.send_message(f"Role {role.mention} has been added to you!",
                                                            ephemeral=True)
                    await interaction.user.add_roles(role, reason="Reaction role")
                    return

            if split[0] == "rrr":
                if role not in interaction.user.roles:
                    await interaction.response.send_message("You already don't have this role!", ephemeral=True)
                    return
                if role in interaction.user.roles:
                    await interaction.response.send_message(f"Role {role.mention} has been removed from you!",
                                                            ephemeral=True)
                    await interaction.user.remove_roles(role, reason="Reaction role")
                    return

            if split[0] == "rrs":
                if role in interaction.user.roles:
                    await interaction.response.send_message(f"You already have selected {role.mention}", ephemeral=True)
                    return

                roles = get_roles(interaction.message)
                await interaction.response.send_message(f"Role {role.mention} was selected out of a choice.",
                                                        ephemeral=True)
                await interaction.user.remove_roles(*roles, reason="Reaction role")
                await interaction.user.add_roles(role, reason="Reaction role")
        except Exception as e:
            nekona_logger.exception("An error occured:")


def setup(bot: Bot):
    bot.add_cog(ReactionRoles(bot))
