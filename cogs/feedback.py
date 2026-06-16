from os import getenv

from aiohttp import ClientSession
from discord import InputTextStyle, Interaction, Cog, SlashCommandGroup, ApplicationContext
from discord.ui import Modal, InputText

from logger import akabot_logger
from utils.message_appends import apply_appends


class BugReportModal(Modal):
    def __init__(self, user_id: int) -> None:
        super().__init__(title="Submit a Bug Report", timeout=600)

        self.user_id = user_id
        title = "Title"
        description = "Description"
        self.title_input = InputText(label=title, style=InputTextStyle.short, max_length=100, min_length=8,
                                     required=True)
        self.description_input = InputText(label=description, style=InputTextStyle.long, max_length=1000,
                                           min_length=20, required=True)

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def submit_bug_report_on_forgejo(self, interaction):
        forgejo_instance = getenv("FORGEJO_INSTANCE")
        forgejo_token = getenv('FORGEJO_TOKEN')
        forgejo_owner = getenv('FORGEJO_OWNER')
        forgejo_project = getenv('FORGEJO_PROJECT')

        issue_body = ("- This bug report was created by {display} ({user} {id}) on Discord\n\n"
                      "---\n\n"
                      "### The issue was described by the user as follows:\n\n"
                      "{desc}".format(display=interaction.user.display_name,
                                      user=interaction.user.name,
                                      id=interaction.user.id,
                                      desc=self.description_input.value))

        async with ClientSession() as session:
            async with session.post(f'https://{forgejo_instance}/api/v1/repos/{forgejo_owner}/{forgejo_project}/issues',
                                    json={
                                        'title': self.title_input.value,
                                        'body': issue_body
                                    },
                                    headers={
                                        'Authorization': f'token {forgejo_token}'
                                    }) as r:
                if r.ok:
                    await interaction.response.send_message(
                        apply_appends(interaction.user.id, "The bug report was submitted successfully"),
                        ephemeral=True)
                else:
                    await interaction.response.send_message(f"Failed to submit bug report: {await r.text()}",
                                                            ephemeral=True)

    async def callback(self, interaction: Interaction):
        try:
            await self.submit_bug_report_on_forgejo(interaction)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await interaction.response.send_message("oops an error occurred trying to report a bug lol", ephemeral=True)


class FeatureModal(Modal):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(title="Submit a Feature", timeout=600)

        title = "Title"
        description = "Description"
        self.title_input = InputText(label=title, style=InputTextStyle.short, max_length=100, min_length=8,
                                     required=True)
        self.description_input = InputText(label=description, style=InputTextStyle.long, max_length=1000,
                                           min_length=20, required=True)

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def submit_feature_on_forgejo(self, interaction):
        forgejo_instance = getenv("FORGEJO_INSTANCE")
        forgejo_token = getenv('FORGEJO_TOKEN')
        forgejo_owner = getenv('FORGEJO_OWNER')
        forgejo_project = getenv('FORGEJO_PROJECT')

        issue_body = ("- This feature request was created by {display} ({user} {id}) on Discord\n\n"
                      "---\n\n"
                      "### The issue was described by the user as follows:\n\n"
                      "{desc}".format(display=interaction.user.display_name,
                                      user=interaction.user.name,
                                      id=interaction.user.id,
                                      desc=self.description_input.value))

        async with ClientSession() as session:
            async with session.post(f'https://{forgejo_instance}/api/v1/repos/{forgejo_owner}/{forgejo_project}/issues',
                                    json={
                                        'title': self.title_input.value,
                                        'body': issue_body
                                    },
                                    headers={
                                        'Authorization': f'token {forgejo_token}'
                                    }) as r:
                if r.ok:
                    await interaction.response.send_message(
                        apply_appends(interaction.user.id, "Feature was submitted successfully"),
                        ephemeral=True)
                else:
                    await interaction.response.send_message(f"Failed to submit feature request: {await r.text()}",
                                                            ephemeral=True)

    async def callback(self, interaction: Interaction):
        try:
            await self.submit_feature_on_forgejo(interaction)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await interaction.response.send_message("", ephemeral=True)


class Feedback(Cog):
    def __init__(self):
        super().__init__()

    feedback_group = SlashCommandGroup(name="feedback")

    @feedback_group.command()
    async def bug_report(self, ctx: ApplicationContext):
        await ctx.response.send_modal(modal=BugReportModal(ctx.user.id))

    @feedback_group.command()
    async def suggestion(self, ctx: ApplicationContext):
        await ctx.response.send_modal(modal=FeatureModal(ctx.user.id))


def setup(bot):
    if getenv("FORGEJO_INSTANCE") is not None and getenv("FORGEJO_TOKEN") is not None and getenv(
            "FORGEJO_OWNER") is not None and getenv("FORGEJO_PROJECT") is not None:
        bot.add_cog(Feedback())
