import os

from discord import (
    ApplicationContext,
    Cog,
    InputTextStyle,
    Interaction,
    SlashCommandGroup,
)
from discord.ui import InputText, Modal

from logger import akabot_logger
from utils.feedback import ForgejoFeedback, GitHubFeedback, DiscordFeedback

FEEDBACK_TYPE = os.getenv("FEEDBACK_TYPE", "none")

feedback_handler = None

if FEEDBACK_TYPE == 'forgejo':
    feedback_handler = ForgejoFeedback()
elif FEEDBACK_TYPE == 'github':
    feedback_handler = GitHubFeedback()
elif FEEDBACK_TYPE == 'discord':
    feedback_handler = DiscordFeedback()

if feedback_handler is not None and not feedback_handler.validate_auth():
    feedback_handler = None


class BugReportModal(Modal):
    def __init__(self, user_id: int) -> None:
        super().__init__(title="Submit a Bug Report", timeout=600)

        self.user_id = user_id
        title = "Title"
        description = "Description"
        self.title_input = InputText(
            label=title,
            style=InputTextStyle.short,
            max_length=100,
            min_length=8,
            required=True,
        )
        self.description_input = InputText(
            label=description,
            style=InputTextStyle.long,
            max_length=1000,
            min_length=20,
            required=True,
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def submit_bug_report_on_forgejo(self, interaction):
        issue_body = (
            "- This bug report was created by {display} ({user} {id}) on Discord\n\n"
            "---\n\n"
            "### The issue was described by the user as follows:\n\n"
            "{desc}".format(
                display=interaction.user.display_name,
                user=interaction.user.name,
                id=interaction.user.id,
                desc=self.description_input.value,
            )
        )

        # This is cursed but should work
        ok, message = feedback_handler.create_issue({
            "user_name": interaction.user.display_name,
            "user": str(interaction.user.id)
        }, f"Bug Report: {self.title_input.value}", issue_body)

        if not ok:
            await interaction.respond(f"An error occurred: {message}", ephemeral=True)
        else:
            await interaction.respond(f"Issue created: {message}", ephemeral=True)

    async def callback(self, interaction: Interaction):
        try:
            await self.submit_bug_report_on_forgejo(interaction)
        except Exception as e:
            akabot_logger.exception(f"Failed to submit bug report from {interaction.user.id}: {e}")
            await interaction.response.send_message(
                "oops an error occurred trying to report a bug lol", ephemeral=True
            )


class FeatureModal(Modal):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(title="Submit a Feature", timeout=600)

        title = "Title"
        description = "Description"
        self.title_input = InputText(
            label=title,
            style=InputTextStyle.short,
            max_length=100,
            min_length=8,
            required=True,
        )
        self.description_input = InputText(
            label=description,
            style=InputTextStyle.long,
            max_length=1000,
            min_length=20,
            required=True,
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def submit_feature_on_forgejo(self, interaction):
        issue_body = (
            "- This feature request was created by {display} ({user} {id}) on Discord\n\n"
            "---\n\n"
            "### The issue was described by the user as follows:\n\n"
            "{desc}".format(
                display=interaction.user.display_name,
                user=interaction.user.name,
                id=interaction.user.id,
                desc=self.description_input.value,
            )
        )

        # This is cursed but should work
        ok, message = feedback_handler.create_issue({
            "user_name": interaction.user.display_name,
            "user": str(interaction.user.id)
        }, f"Suggestion: {self.title_input.value}", issue_body)

        if not ok:
            await interaction.respond(f"An error occured: {message}", ephemeral=True)
        else:
            await interaction.respond(f"Issue created: {message}", ephemeral=True)


    async def callback(self, interaction: Interaction):
        try:
            await self.submit_feature_on_forgejo(interaction)
        except Exception as e:
            akabot_logger.exception(f"Failed to submit feature request from {interaction.user.id}: {e}")
            await interaction.response.send_message("", ephemeral=True)


class Feedback(Cog):
    def __init__(self):
        super().__init__()

    feedback_group = SlashCommandGroup(name="feedback")

    @feedback_group.command()
    async def bug_report(self, ctx: ApplicationContext):
        if feedback_handler is None:
            await ctx.respond("Not available", ephemeral=True)
        await ctx.response.send_modal(modal=BugReportModal(ctx.user.id))

    @feedback_group.command()
    async def suggestion(self, ctx: ApplicationContext):
        if feedback_handler is None:
            await ctx.respond("Not available", ephemeral=True)
        await ctx.response.send_modal(modal=FeatureModal(ctx.user.id))


def setup(bot):
    if feedback_handler is not None:
        bot.add_cog(Feedback())
