import os

from flask import Blueprint, flash, redirect, render_template, request, session
from mdparser import parse_markdown
from sqlalchemy import delete, update

from database import engine, mail
from utils.mail import (
    add_mail,
    get_all_mail,
    get_unread_mail,
    get_unread_mail_count,
    mark_as_read,
)
from web.webutils.tokens import authorize, get_token_data

mail_bp = Blueprint("settings_mail", __name__, template_folder="templates")


@mail_bp.route("/settings/mail", methods=["GET", "POST"])
def settings_mail_index():
    authorization = authorize("/settings/mail")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    is_admin = auth["user"] == os.getenv("BOT_OWNER_ID", "-1")

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "mark_read":
            for message in get_unread_mail(auth["user"]):
                mark_as_read(auth["user"], message[0])
            flash("Marked all mail as read")
        elif is_admin and action == "create":
            author = request.form.get("author", "").strip()
            post = request.form.get("post", "")
            if 2 <= len(author) <= 32 and 4 <= len(post) <= 1000:
                add_mail(author, post)
                flash("Created mail post")
            else:
                flash("Author must be 2-32 characters and the post 4-1000 characters")
        elif is_admin and action == "update":
            message_id = request.form.get("id", "")
            author = request.form.get("author", "").strip()
            post = request.form.get("post", "")
            if not message_id.isnumeric():
                flash("Invalid mail id")
            elif not (2 <= len(author) <= 32 and 4 <= len(post) <= 1000):
                flash("Author must be 2-32 characters and the post 4-1000 characters")
            else:
                with engine.begin() as c:
                    c.execute(
                        update(mail)
                        .where(mail.c.id == int(message_id))
                        .values(author=author, text=post)
                    )
                flash("Saved mail post")
        elif is_admin and action == "delete":
            message_id = request.form.get("id", "")
            if message_id.isnumeric():
                with engine.begin() as c:
                    c.execute(delete(mail).where(mail.c.id == int(message_id)))
                flash("Deleted mail post")
            else:
                flash("Invalid mail id")

        return redirect(
            f"/settings/mail?tab={request.form.get('_tab', 'inbox')}", 303
        )

    active_tab = request.args.get("tab", "inbox")
    if active_tab not in {"inbox", "compose"} or (
        active_tab == "compose" and not is_admin
    ):
        active_tab = "inbox"

    all_mail_rows = get_all_mail(auth["user"])
    raw_mail = [
        {
            "id": i[0],
            "text": i[1],
            "author": i[2],
            "created_at": i[4],
        }
        for i in all_mail_rows
    ]
    display_mail = [
        {
            "id": i[0],
            "text": i[1] if is_admin else parse_markdown(i[1], full_html=False),
            "author": i[2],
            "created_at": i[4],
        }
        for i in all_mail_rows
    ]

    unread_messages = [
        {
            "id": i[0],
            "text": parse_markdown(i[1], full_html=False),
            "author": i[2],
            "created_at": i[3],
        }
        for i in get_unread_mail(auth["user"])
    ]
    unread_ids = {message["id"] for message in unread_messages}
    past_messages = [
        message for message in display_mail if message["id"] not in unread_ids
    ]
    unread_count = get_unread_mail_count(auth["user"])

    return render_template(
        "mail.html",
        admin=is_admin,
        unread=unread_count,
        unread_messages=unread_messages,
        past_messages=past_messages,
        all=raw_mail,
        active_tab=active_tab,
    )
