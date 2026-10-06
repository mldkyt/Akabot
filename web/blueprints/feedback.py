import os
from pprint import pprint

import requests
from flask import Blueprint, render_template, session, request, flash, redirect, make_response
from sqlalchemy import insert, delete, select

from database import engine, web_feedback_bans
from web.webutils.quick_response import quick_response
from web.webutils.tokens import authorize, get_token_data

feedback_bp = Blueprint("feedback", __name__)

FORGEJO_INSTANCE = os.getenv("FORGEJO_INSTANCE")
FORGEJO_TOKEN = os.getenv("FORGEJO_TOKEN")
FORGEJO_OWNER = os.getenv("FORGEJO_OWNER")
FORGEJO_PROJECT = os.getenv("FORGEJO_PROJECT")

def handle_feedback_post(auth):
    with engine.begin() as c:
        is_banned = c.execute(
            select(web_feedback_bans)
            .where(web_feedback_bans.c.uid == auth["user"])
        ).fetchone()

    if is_banned is not None:
        flash("You are banned from posting feedback.")
        return

    if "title" not in request.form or \
        "body" not in request.form:
        return None

    if not 4 <= len(request.form["title"]) <= 50:
        flash("The title has an invalid length")
        return None

    if not 10 <= len(request.form["body"]) <= 1200:
        flash("The body has an invalid length")
        return None

    res = requests.post(f"https://{FORGEJO_INSTANCE}/api/v1/repos/{FORGEJO_OWNER}/{FORGEJO_PROJECT}/issues", headers={
        "Authorization": f"Bearer {FORGEJO_TOKEN}"
    }, json={
        "title": request.form["title"],
        "body": f"The user {auth['user_name']} ({auth['user']}) has submitted an issue through the feedback form:\n\n{request.form['body']}"
    })

    if res.status_code == 201:
        res_json = res.json()
        return redirect(res_json["html_url"], 303)
    else:
        print(res.status_code, res.text)
        flash("The server for tracking issues returned an unknown error, your issue was not submitted. We are sorry for the inconvenience")

    return None


@feedback_bp.route("/settings/feedback", methods=["GET", "POST"])
def feedback_page():
    authorization = authorize("/settings/feedback")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if FORGEJO_INSTANCE is None or FORGEJO_TOKEN is None or FORGEJO_OWNER is None or FORGEJO_PROJECT is None:
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
