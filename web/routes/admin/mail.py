from flask import Blueprint, request, render_template, redirect, make_response
from sqlalchemy import delete, update

from database import engine, mail
from utils.mail import add_mail, get_mail_by_id
from web.webutils.mail import get_all_mail

mail_blueprint = Blueprint('mail', __name__, template_folder='templates')


@mail_blueprint.route('/admin/mail/add', methods=["POST", "GET"])
def admin_mail_add():
    if request.method == "POST":
        if "author" not in request.form or "post" not in request.form:
            return render_template("mail_add.html", error="Invalid post parameters")

        if 2 > len(request.form['author'].strip()) > 32 or 4 > len(request.form['post']) > 1000:
            return render_template("mail_add.html", error="Invalid length of post parameters (author or post)")

        add_mail(request.form['author'], request.form['post'])

        return redirect("/admin/mail", 303)

    return render_template("mail_add.html")


@mail_blueprint.route('/admin/mail/edit/<id>', methods=["POST", "GET"])
def admin_mail_edit(id: str):
    if not id.isnumeric():
        response = make_response("The ID has to be a number")
        response.status_code = 400
        return response

    if request.method == "POST":
        if "author" not in request.form or "post" not in request.form:
            return render_template("mail_edit.html", error="Invalid post parameters")

        if 2 > len(request.form['author'].strip()) > 32 or 4 > len(request.form['post']) > 1000:
            return render_template("mail_edit.html", error="Invalid length of post parameters (author or post)")

        with engine.begin() as c:
            c.execute(
                update(mail)
                .where(mail.c.id == int(id))
                .values(author=request.form['author'], text=request.form['post'])
            )

        return redirect("/admin/mail", 303)

    data = get_mail_by_id(int(id))

    return render_template("mail_edit.html", item=data)


@mail_blueprint.route('/admin/mail')
def admin_mail():
    mail_list = get_all_mail()

    mail_list = [(i[0], i[1], i[2][:30] + "...", i[3], i[4]) for i in mail_list]

    return render_template("mail_list.html", mail=mail_list)


@mail_blueprint.route('/admin/mail/delete/<id>')
def delete_mail(id: str):
    if not id.isnumeric():
        response = make_response("The ID has to be a number")
        response.status_code = 400
        return response

    if "confirm" in request.args and request.args["confirm"] == "1":
        with engine.begin() as c:
            c.execute(
                delete(mail)
                .where(mail.c.id == int(id))
            )

        return redirect("/admin/mail", 303)

    if "back" in request.args and request.args["back"] == "1":
        return redirect("/admin/mail", 303)

    data = get_mail_by_id(int(id))

    return render_template("mail_delete.html", item=data)
