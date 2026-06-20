from flask import Flask

from web.routes.admin.mail import mail_blueprint

app = Flask(__name__)

# Admin mail routes
app.register_blueprint(mail_blueprint)


def main():
    app.run("::", 8080)


if __name__ == '__main__':
    main()
