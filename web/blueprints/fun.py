from flask import Blueprint, session, render_template, request

from database import engine
from utils.fun import setting_disable_yuri_command, setting_disable_yaoi_command, setting_allow_rp_commands
from web.webutils.tokens import authorize, get_token_data

fun_commands_bp = Blueprint("fun", __name__, template_folder="templates")

def handle_post(auth):
    with engine.begin() as c:
        if "yuri" in request.form:
            setting_disable_yuri_command.set(c, auth["guild"], "false")
        else:
            setting_disable_yuri_command.set(c, auth["guild"], "true")

        if "yaoi" in request.form:
            setting_disable_yaoi_command.set(c, auth["guild"], "false")
        else:
            setting_disable_yaoi_command.set(c, auth["guild"], "true")

        if "rp" in request.form:
            setting_allow_rp_commands.set(c, auth["guild"], "true")
        else:
            setting_allow_rp_commands.set(c, auth["guild"], "false")


@fun_commands_bp.route("/settings/fun", methods=["GET", "POST"])
def fun_index():
    authorization = authorize("/settings/fun")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_post(auth)

    with engine.begin() as c:
        yuri_command = setting_disable_yuri_command.get(c, auth["guild"]) != "true"
        yaoi_command = setting_disable_yaoi_command.get(c, auth["guild"]) != "true"
        rp_commands = setting_allow_rp_commands.get(c, auth["guild"]) == "true"

    return render_template("fun.html", yuri=yuri_command, yaoi=yaoi_command, rp=rp_commands)
