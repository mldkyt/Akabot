import os

import requests
from discord import Bot, Embed

from database import engine
from utils.tasks import create_task, register_task


class Feedback:
    def __init__(self):
        pass

    def validate_auth(self) -> bool:
        return False

    def create_issue(self, auth_data, title: str, body: str) -> tuple[bool, str]:
        pass


class ForgejoFeedback(Feedback):
    def __init__(self):
        self.instance = os.getenv("FORGEJO_INSTANCE")
        self.token = os.getenv("FORGEJO_TOKEN")
        self.owner = os.getenv("FORGEJO_OWNER")
        self.project = os.getenv("FORGEJO_PROJECT")

    def validate_auth(self) -> bool:
        return self.instance is not None and \
            len(self.instance) > 0 and \
            self.token is not None and \
            len(self.token) > 0 and \
            self.owner is not None and \
            len(self.owner) > 0 and \
            self.project is not None and \
            len(self.project) > 0

    def create_issue(self, auth_data, title: str, body: str) -> tuple[bool, str]:
        if not 4 <= len(title) <= 50:
            return False, "The title has an invalid length"

        if not 10 <= len(body) <= 1200:
            return False, "The body has an invalid length"

        try:
            res = requests.post(f"https://{self.instance}/api/v1/repos/{self.owner}/{self.project}/issues",
                                headers={
                                    "Authorization": f"Bearer {self.token}"
                                }, json={
                    "title": title,
                    "body": f"The user {auth_data['user_name']} ({auth_data['user']}) has submitted an issue through the feedback form:\n\n{body}"
                })
        except Exception as e:
            return False, f"Error occurred when sending request: {e}"

        if res.status_code == 201:
            res_json = res.json()
            return True, res_json["html_url"]
        else:
            print(res.status_code, res.text)
            return False, "The server for tracking issues returned an unknown error, your issue was not submitted. We are sorry for the inconvenience"

class GitHubFeedback(Feedback):
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = os.getenv("GITHUB_OWNER")
        self.project = os.getenv("GITHUB_PROJECT")

    def validate_auth(self) -> bool:
        return self.token is not None and \
            len(self.token) > 0 and \
            self.owner is not None and \
            len(self.owner) > 0 and \
            self.project is not None and \
            len(self.project) > 0

    def create_issue(self, auth_data, title: str, body: str) -> tuple[bool, str]:
        if not 4 <= len(title) <= 50:
            return False, "The title has an invalid length"

        if not 10 <= len(body) <= 1200:
            return False, "The body has an invalid length"

        try:
            response = requests.post(f"https://api.github.com/repos/{self.owner}/{self.project}/issues", headers={
                "Authorization": f"Bearer {self.token}"
            }, json={
                "title": title,
                "body": f"The user {auth_data['user_name']} ({auth_data['user']}) has submitted an issue through the feedback form:\n\n{body}"
            })
        except Exception as e:
            return False, f"Error occurred when sending request: {e}"

        if not response.ok:
            return False, "GitHub returned an unknown error, your issue was not submitted. We are sorry for the inconvenience"

        response_json = response.json()
        return True, response_json["html_url"]

class DiscordFeedback(Feedback):
    def __init__(self):
        self.channel = os.getenv("FEEDBACK_CHANNEL")
        self.guild = os.getenv("FEEDBACK_GUILD")

    def validate_auth(self) -> bool:
        return self.channel is not None and \
            len(self.channel) > 0 and \
            self.guild is not None and \
            len(self.guild) > 0

    def create_issue(self, auth_data, title: str, body: str) -> tuple[bool, str]:
        if not 4 <= len(title) <= 50:
            return False, "The title has an invalid length"

        if not 10 <= len(body) <= 1200:
            return False, "The body has an invalid length"

        with engine.begin() as c:
            create_task(c, "bot", "feedbackSubmit", {
                "title": title,
                "body": f"The user {auth_data['user_name']} ({auth_data['user']}) has submitted an issue through the feedback form:\n\n{body}"
            })

        return True, ""

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


@register_task("feedbackSubmit")
async def feedback_submit(bot: Bot, data: dict):
    if not isinstance(feedback_handler, DiscordFeedback):
        return

    guild = bot.get_guild(int(feedback_handler.guild))
    if guild is None:
        raise ValueError("guild")

    channel = bot.get_channel(int(feedback_handler.channel))
    if channel is None:
        raise ValueError("channel")

    await channel.send(
        embed=Embed(
            title=data["title"],
            description=data["body"]
        )
    )
