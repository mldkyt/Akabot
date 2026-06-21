from flask import Blueprint, render_template

from web.webutils.tokens import authorize

settings_index_bp = Blueprint("settings_index", __name__, template_folder='templates')


@settings_index_bp.route("/settings")
def settings_index():
    authorization = authorize("/settings")
    if authorization is not None:
        return authorization

    return render_template("index.html")
