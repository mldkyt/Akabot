import os

from flask import Blueprint, session, render_template, request, flash, redirect
from mdparser import parse_markdown
from sqlalchemy import update, delete

from database import engine, mail
from utils.mail import get_all_mail, get_unread_mail_count, get_unread_mail, mark_as_read, add_mail, get_mail_by_id
from web.webutils.quick_response import quick_response
from web.webutils.tokens import authorize, get_token_data

mail_bp = Blueprint("settings_mail", __name__)

@mail_bp.route("/settings/mail")
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

    is_admin = auth["user"] == os.getenv("BOT_OWNER_ID", "-1")
    all_mail = [{
        "id": i[0],
        "text": i[1] if is_admin else parse_markdown(i[1], full_html=False),
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

    mail = [i for i in all_mail if i not in unread]


    return render_template("mail.html", admin=is_admin, unread=unread_count, unread_messages=unread, past_messages=mail[:10], all=all_mail)

@mail_bp.route('/settings/mail/add', methods=["POST"])
def admin_mail_add():
    authorization = authorize("/settings/mail")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    is_admin = auth["user"] == os.getenv("BOT_OWNER_ID", "-1")
    if not is_admin:
        return quick_response("Forbidden", 403)

    if "author" not in request.form or "post" not in request.form:
        return redirect("/settings/mail", 303)

    if 2 > len(request.form['author'].strip()) > 32 or 4 > len(request.form['post']) > 1000:
        return redirect("/settings/mail", 303)

    add_mail(request.form['author'], request.form['post'])

    return redirect("/settings/mail", 303)

@mail_bp.route('/settings/mail/edit/<id>', methods=["POST"])
def admin_mail_edit(id: str):
    authorization = authorize("/settings/mail")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    is_admin = auth["user"] == os.getenv("BOT_OWNER_ID", "-1")
    if not is_admin:
        return quick_response("Forbidden", 403)

    if not id.isnumeric():
        return quick_response("The ID must be a number", 400)

    if "author" not in request.form or "post" not in request.form:
        return redirect("/settings/mail", 303)

    if 2 > len(request.form['author'].strip()) > 32 or 4 > len(request.form['post']) > 1000:
        return redirect("/settings/mail")

    with engine.begin() as c:
        c.execute(
            update(mail)
            .where(mail.c.id == int(id))
            .values(author=request.form['author'], text=request.form['post'])
        )

    return redirect("/settings/mail", 303)


@mail_bp.route('/settings/mail/delete/<id>')
def delete_mail(id: str):
    authorization = authorize("/settings/mail")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    is_admin = auth["user"] == os.getenv("BOT_OWNER_ID", "-1")
    if not is_admin:
        return quick_response("Forbidden", 403)

    if not id.isnumeric():
        return quick_response("The ID has to be a number", 400)

    if "confirm" in request.args and request.args["confirm"] == "1":
        with engine.begin() as c:
            c.execute(
                delete(mail)
                .where(mail.c.id == int(id))
            )

        return redirect("/settings/mail", 303)

    data = get_mail_by_id(int(id))

    return render_template("mail_delete.html", item=data)
