import logging
import os

import sentry_sdk
from dotenv import load_dotenv
from flask import Flask, request, session
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from werkzeug.exceptions import HTTPException

from web.blueprints.anti_raid import anti_raid_bp
from web.blueprints.automod_actions import automod_actions_bp
from web.blueprints.chat_revive import chat_revive_bp
from web.blueprints.chat_streaks import chat_streaks_bp
from web.blueprints.chat_summary import chat_summary_bp
from web.blueprints.counting import counting_bp
from web.blueprints.feedback import feedback_bp
from web.blueprints.fun import fun_commands_bp
from web.blueprints.index import settings_index_bp
from web.blueprints.leveling import leveling_bp
from web.blueprints.logging import logging_bp
from web.blueprints.mail import mail_bp
from web.blueprints.main_page import main_page_bp
from web.blueprints.markov import markov_bp
from web.blueprints.meow_back import meow_back_bp
from web.blueprints.message_counting import message_counting_bp
from web.blueprints.moderation import moderation_bp
from web.blueprints.periodic_messages import periodic_messages_bp
from web.blueprints.reaction_roles import reaction_roles_bp
from web.blueprints.premium import premium_bp
from web.blueprints.roles_on_join import roles_on_join_bp
from web.blueprints.statistic_channels import statistic_channels_bp
from web.blueprints.sticky_messages import sticky_messages_bp
from web.blueprints.suggestions import suggestions_bp
from web.blueprints.tags import tags_bp
from web.blueprints.temporary_vcs import temporary_vcs_bp
from web.blueprints.verification import verification_bp
from web.blueprints.voting import voting_bp
from web.blueprints.welcome_goodbye import welcome_goodbye_bp

from utils.premium import premium_enabled

load_dotenv()

if os.getenv("SENTRY_SDK"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_SDK"),
        integrations=[
            FlaskIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=True,
        max_request_body_size="always",
        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
    )

app = Flask(__name__, static_folder="web/static", static_url_path="/static")

app.secret_key = os.getenv("WEB_SECRET", "1234")


@app.errorhandler(Exception)
def handle_unexpected_exception(error):
    if isinstance(error, HTTPException):
        return error

    app.logger.exception("Unhandled exception")
    return "Internal Server Error", 500

app.context_processor(lambda: {"premium_enabled": premium_enabled()})

PAGE_USAGE = {
    "/settings/counting": ("Counting channels", 1),
    "/settings/leveling": ("Leveling rewards", 3),
    "/settings/moderation": ("Moderator roles", 5),
    "/settings/welcome_goodbye": None,
    "/settings/logging": ("Logging channels", 1),
    "/settings/automod_actions": ("Automod actions", 3),
    "/settings/chat_summary": ("Chat summary channels", 1),
    "/settings/roles_on_join": ("Roles on join", 3),
    "/settings/chat_revive": ("Chat revive channels", 1),
    "/settings/temporary_vcs": ("Temporary voice channels", 3),
    "/settings/statistic_channels": ("Statistic channels", 2),
    "/settings/verification": ("Verification setups", 1),
    "/settings/anti_raid": ("Anti raid protections", 3),
    "/settings/message_counting": ("Message counting rewards", 3),
    "/settings/periodic_messages": ("Periodic messages", 2),
    "/settings/sticky_messages": ("Sticky messages", 1),
    "/settings/suggestions": ("Suggestion channels", 1),
    "/settings/tags": ("Tags", 3),
    "/settings/markov": ("Markov channels", 1),
    "/settings/reaction_roles": ("Reaction role messages", 3),
}


@app.context_processor
def inject_premium_usage():
    if "token" not in session:
        return {}

    match = None
    for path, config in PAGE_USAGE.items():
        if request.path.startswith(path):
            match = (path, config)
            break

    if match is None:
        return {}

    auth = get_token_data(session["token"])
    if auth is None:
        return {}

    with engine.begin() as c:
        if not premium_enabled():
            return {"premium_usage": None}

        items = {i["name"]: i for i in get_usage(c, auth["guild"])}

        if match[1] is None:
            usage = items["Welcome messages"]["usage"] + items["Goodbye messages"]["usage"]
            return {
                "premium_usage": usage_bar(
                    c, auth["guild"], "Welcome & Goodbye messages", usage, 2
                )
            }

        name, free_limit = match[1]
        item = items.get(name)
        if item is None:
            return {}

        return {
            "premium_usage": usage_bar(
                c, auth["guild"], name, item["usage"], free_limit
            )
        }

# Settings
app.register_blueprint(settings_index_bp)
app.register_blueprint(automod_actions_bp)
app.register_blueprint(chat_revive_bp)
app.register_blueprint(chat_streaks_bp)
app.register_blueprint(chat_summary_bp)
app.register_blueprint(counting_bp)
app.register_blueprint(leveling_bp)
app.register_blueprint(logging_bp)
app.register_blueprint(mail_bp)
app.register_blueprint(meow_back_bp)
app.register_blueprint(moderation_bp)
app.register_blueprint(roles_on_join_bp)
app.register_blueprint(statistic_channels_bp)
app.register_blueprint(temporary_vcs_bp)
app.register_blueprint(verification_bp)
app.register_blueprint(welcome_goodbye_bp)
app.register_blueprint(fun_commands_bp)
app.register_blueprint(feedback_bp)
app.register_blueprint(suggestions_bp)
app.register_blueprint(sticky_messages_bp)
app.register_blueprint(periodic_messages_bp)
app.register_blueprint(reaction_roles_bp)
app.register_blueprint(markov_bp)
app.register_blueprint(tags_bp)
app.register_blueprint(anti_raid_bp)
app.register_blueprint(message_counting_bp)
app.register_blueprint(premium_bp)

if os.getenv("TOPGG_WEBHOOK_SECRET") is not None:
    app.register_blueprint(voting_bp)

app.register_blueprint(main_page_bp)


def main():
    app.run("::", 8080)


if __name__ == "__main__":
    main()
