import os

from flask import Flask

from web.routes.admin.mail import mail_blueprint
from web.routes.settings.automod_actions import automod_actions_bp
from web.routes.settings.chat_revive import chat_revive_bp
from web.routes.settings.chat_summary import chat_summary_bp
from web.routes.settings.index import settings_index_bp

app = Flask(__name__)

app.secret_key = os.getenv("WEB_SECRET", "1234")

# Admin mail routes
app.register_blueprint(mail_blueprint)

# Settings
app.register_blueprint(settings_index_bp)
app.register_blueprint(automod_actions_bp)
app.register_blueprint(chat_revive_bp)
app.register_blueprint(chat_summary_bp)

def main():
    app.run("::", 8080)


if __name__ == '__main__':
    main()
