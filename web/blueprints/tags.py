from flask import Blueprint, flash, redirect, render_template, request, session
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

    if request.method == "POST":
        action = request.form.get("action", "create")
        tag_id = request.form.get("id", "")
        keyword = request.form.get("keyword", "").strip()
        content = request.form.get("content", "").strip()

        with engine.begin() as c:
            if action == "delete":
                if tag_id.isnumeric():
                    c.execute(
                        delete(tags).where(
                            (tags.c.id == int(tag_id))
                            & (tags.c.guild_id == auth["guild"])
                        )
                    )
                    flash("Deleted tag")
            elif not keyword or not content:
                flash("A tag needs a keyword and content")
            elif action == "update" and tag_id.isnumeric():
                c.execute(
                    update(tags)
                    .where(
                        (tags.c.id == int(tag_id))
                        & (tags.c.guild_id == auth["guild"])
                    )
                    .values(keyword=keyword, content=content)
                )
                flash("Saved tag")
            else:
                c.execute(
                    insert(tags).values(
                        guild_id=auth["guild"],
                        keyword=keyword,
                        content=content,
                    )
                )
                flash("Added tag")

        return redirect(f"/settings/tags?tab={request.form.get('_tab', 'tags')}", 303)

    active_tab = request.args.get("tab", "tags")
    if active_tab not in {"tags", "create"}:
        active_tab = "tags"

    with engine.begin() as c:
        tags_data = [
            {"id": i[0], "keyword": i[1], "content": i[2]}
            for i in c.execute(
                select(tags.c.id, tags.c.keyword, tags.c.content)
                .where(tags.c.guild_id == auth["guild"])
                .order_by(tags.c.keyword)
            ).fetchall()
        ]

    return render_template("tags.html", tags=tags_data, active_tab=active_tab)
