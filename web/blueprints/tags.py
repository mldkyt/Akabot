from flask import Blueprint, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, tags
from web.webutils.tokens import authorize, get_token_data

tags_bp = Blueprint("tags_bp", __name__, template_folder="templates")


@tags_bp.route("/settings/tags", methods=["GET", "POST"])
def template_index():
    authorization = authorize("/settings/tags")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if request.form.get("keyword") and request.form.get("content"):
                if request.form.get("id"):
                    if not request.form["id"].isnumeric():
                        return quick_response("Invalid tag id", 400)

                    c.execute(
                        update(tags)
                        .where(
                            (tags.c.id == int(request.form["id"]))
                            & (tags.c.guild_id == auth["guild"])
                        )
                        .values(
                            keyword=request.form["keyword"],
                            content=request.form["content"],
                        )
                    )
                else:
                    c.execute(
                        insert(tags).values(
                            guild_id=auth["guild"],
                            keyword=request.form["keyword"],
                            content=request.form["content"],
                        )
                    )

            if request.form.get("delete"):
                if not request.form["delete"].isnumeric():
                    return quick_response("Invalid tag id", 400)

                c.execute(
                    delete(tags).where(
                        (tags.c.id == int(request.form["delete"]))
                        & (tags.c.guild_id == auth["guild"])
                    )
                )

        tags_data = [
            {"id": i[0], "keyword": i[1], "content": i[2]}
            for i in c.execute(
                select(tags.c.id, tags.c.keyword, tags.c.content).where(
                    tags.c.guild_id == auth["guild"]
                )
            ).fetchall()
        ]

    return render_template("tags.html", tags=tags_data)
