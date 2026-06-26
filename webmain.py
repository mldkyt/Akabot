import os

from dotenv import load_dotenv
from flask import Flask

from web.blueprints.automod_actions import automod_actions_bp
from web.blueprints.chat_revive import chat_revive_bp
from web.blueprints.chat_summary import chat_summary_bp
from web.blueprints.counting import counting_bp
from web.blueprints.feedback import feedback_bp
from web.blueprints.fun import fun_commands_bp
from web.blueprints.index import settings_index_bp
from web.blueprints.leveling import leveling_bp
from web.blueprints.logging import logging_bp
from web.blueprints.mail import mail_bp
from web.blueprints.main_page import main_page_bp
from web.blueprints.meow_back import meow_back_bp
from web.blueprints.moderation import moderation_bp
from web.blueprints.roles_on_join import roles_on_join_bp
from web.blueprints.statistic_channels import statistic_channels_bp
from web.blueprints.temporary_vcs import temporary_vcs_bp
from web.blueprints.verification import verification_bp
from web.blueprints.welcome_goodbye import welcome_goodbye_bp

load_dotenv()

app = Flask(__name__,
            static_folder='web/static',
            static_url_path='/static')

app.secret_key = os.getenv("WEB_SECRET", "1234")

app.register_blueprint(main_page_bp)

# Settings
app.register_blueprint(settings_index_bp)
app.register_blueprint(automod_actions_bp)
app.register_blueprint(chat_revive_bp)
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

def main():
    app.run("::", 8080)


if __name__ == '__main__':
    main()
