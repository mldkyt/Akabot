import os

from flask import Blueprint, render_template, session, request, flash, redirect
from sqlalchemy import insert, delete, select

from database import engine, web_feedback_bans
from utils.feedback import ForgejoFeedback, GitHubFeedback, DiscordFeedback
from web.webutils.quick_response import quick_response
from web.webutils.tokens import authorize, get_token_data

feedback_bp = Blueprint("feedback", __name__)

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

def handle_feedback_post(auth):
    if feedback_handler is None:
        return None

    with engine.begin() as c:
        is_banned = c.execute(
            select(web_feedback_bans)
            .where(web_feedback_bans.c.uid == auth["user"])
        ).fetchone()

    if is_banned is not None:
        flash("You are banned from posting feedback.")
        return None

    if "title" not in request.form or \
            "body" not in request.form:
        return None

    ok, message = feedback_handler.create_issue(auth, request.form["title"], request.form["body"])

    if ok:
        return redirect(message, 303)
    else:
        flash(message)
        return None


@feedback_bp.route("/settings/feedback", methods=["GET", "POST"])
def feedback_page():
    authorization = authorize("/settings/feedback")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if feedback_handler is None:
        return render_template("feedback.html", disabled=True)

    if request.method == "POST":
        post_result = handle_feedback_post(auth)
        if post_result is not None:
            return post_result

    is_admin = auth["user"] == os.getenv("BOT_OWNER_ID", "-1")

    return render_template("feedback.html", admin=is_admin, owner_id=os.getenv("BOT_OWNER_ID", "-1"))

@feedback_bp.route("/settings/feedback/ban", methods=["POST"])
def feedback_ban():
    authorization = authorize("/settings/feedback")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    is_admin = auth["user"] == os.getenv("BOT_OWNER_ID", "-1")
    if not is_admin:
        return quick_response("Forbidden", 403)

    with engine.begin() as c:
        c.execute(
            insert(web_feedback_bans)
            .values(uid=request.form["user"])
        )

    return redirect("/settings/feedback", 303)

@feedback_bp.route("/settings/feedback/unban", methods=["POST"])
def feedback_unban():
    authorization = authorize("/settings/feedback")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    is_admin = auth["user"] == os.getenv("BOT_OWNER_ID", "-1")
    if not is_admin:
        return quick_response("Forbidden", 403)

    with engine.begin() as c:
        c.execute(
            delete(web_feedback_bans)
            .where(web_feedback_bans.c.uid == request.form["user"])
        )

    return redirect("/settings/feedback", 303)
