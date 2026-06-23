from flask import Blueprint, session, render_template, request, flash, redirect
from mdparser import parse_markdown

from utils.mail import get_all_mail, get_unread_mail_count, get_unread_mail, mark_as_read
from web.webutils.tokens import authorize, get_token_data

settings_mail_bp = Blueprint("settings_mail", __name__)

@settings_mail_bp.route("/settings/mail")
def settings_mail_index():
    authorization = authorize("/settings/mail")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.args.get("read") == "1":
        for mail in get_unread_mail(auth["user"]):
            mark_as_read(auth["user"], mail[0])
            flash("Marked all mail as read")
            return redirect("/settings/mail")

    mail = [{
        "id": i[0],
        "text": parse_markdown(i[1], full_html=False),
        "author": i[2],
        "created_at": i[4]
    } for i in get_all_mail(auth["user"])]
    unread_count = get_unread_mail_count(auth["user"])
    unread = [{
        "id": i[0],
        "text": parse_markdown(i[1], full_html=False),
        "author": i[2],
        "created_at": i[3]
    } for i in get_unread_mail(auth["user"])]

    mail = [i for i in mail if i not in unread]

    return render_template("mail.html", unread=unread_count, unread_messages=unread, past_messages=mail[:10])
