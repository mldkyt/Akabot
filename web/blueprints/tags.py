from flask import Blueprint, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, tags
from utils.premium import get_limit, get_premium_context
from web.webutils.quick_response import quick_response
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
                    limit = get_limit(c, auth["guild"], 3)
                    tag_count = len(c.execute(
                        select(tags.c.id).where(tags.c.guild_id == auth["guild"])
                    ).fetchall())
                    if limit is not None and tag_count >= limit:
                        return quick_response("Free plan is limited to 3 tags", 400)

                    c.execute(
                        insert(tags).values(
                            guild_id=auth["guild"],
                            keyword=request.form["keyword"],
                            content=request.form["content"],
                        )
                    )

            if request.form.get("delete"):
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

        premium = get_premium_context(c, auth["guild"])

    return render_template("tags.html", tags=tags_data, premium=premium)
