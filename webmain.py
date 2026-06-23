import os

from flask import Flask

from web.routes.admin.mail import mail_blueprint
from web.routes.settings.automod_actions import automod_actions_bp
from web.routes.settings.chat_revive import chat_revive_bp
from web.routes.settings.chat_summary import chat_summary_bp
from web.routes.settings.counting import counting_bp
from web.routes.settings.index import settings_index_bp
from web.routes.settings.leveling import leveling_bp
from web.routes.settings.logging import logging_bp
from web.routes.settings.mail import settings_mail_bp
from web.routes.settings.meow_back import meow_back_bp

app = Flask(__name__)

app.secret_key = os.getenv("WEB_SECRET", "1234")

# Admin mail routes
app.register_blueprint(mail_blueprint)

# Settings
app.register_blueprint(settings_index_bp)
app.register_blueprint(automod_actions_bp)
app.register_blueprint(chat_revive_bp)
app.register_blueprint(chat_summary_bp)
app.register_blueprint(counting_bp)
app.register_blueprint(leveling_bp)
app.register_blueprint(logging_bp)
app.register_blueprint(settings_mail_bp)
app.register_blueprint(meow_back_bp)

def main():
    app.run("::", 8080)


if __name__ == '__main__':
    main()
