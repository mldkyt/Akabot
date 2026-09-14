from flask import Blueprint, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, sticky_messages, synced_channels
from utils.premium import get_limit, get_premium_context
from web.webutils.quick_response import quick_response
from web.webutils.tokens import authorize, get_token_data

sticky_messages_bp = Blueprint("sticky_messages", __name__, template_folder="templates")


@sticky_messages_bp.route("/settings/sticky_messages", methods=["GET", "POST"])
def sticky_messages_index():
    authorization = authorize("/settings/sticky_messages")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if request.form.get("channel") and request.form.get("content"):
                existing = c.execute(
                    select(sticky_messages).where(
                        sticky_messages.c.channel_id == request.form["channel"]
                    )
                ).fetchone()

                if existing:
                    c.execute(
                        update(sticky_messages)
                        .values(content=request.form["content"])
                        .where(sticky_messages.c.channel_id == request.form["channel"])
                    )

                else:
                    limit = get_limit(c, auth["guild"], 1)
                    sticky_count = len(c.execute(
                        select(sticky_messages.c.channel_id).where(sticky_messages.c.guild_id == auth["guild"])
                    ).fetchall())
                    if limit is not None and sticky_count >= limit:
                        return quick_response("Free plan is limited to 1 sticky message", 400)

                    c.execute(
                        insert(sticky_messages).values(
                            channel_id=request.form["channel"],
                            content=request.form["content"],
                            guild_id=auth["guild"],
                        ),
                    )
            elif request.form.get("delete"):
                c.execute(
                    delete(sticky_messages).where(
                        sticky_messages.c.channel_id == request.form["delete"]
                    )
                )

        text_channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.ctype == "text")
                    & (synced_channels.c.gid == auth["guild"])
                )
            ).fetchall()
        ]

        sticky_messages_data = []

        for i in c.execute(
            select(sticky_messages.c.channel_id, sticky_messages.c.content).where(
                sticky_messages.c.guild_id == auth["guild"]
            )
        ).fetchall():
            channel_info = c.execute(
                select(synced_channels.c.cname).where(synced_channels.c.cid == i[0])
            ).fetchone()

            sticky_messages_data.append(
                {
                    "id": i[0],
                    "content": i[1],
                    "name": channel_info[0] if channel_info else "Unknown Channel",
                }
            )

    return render_template(
        "sticky_messages.html",
        text_channels=text_channels,
        sticky_messages=sticky_messages_data,
        premium=get_premium_context(c, auth["guild"]),
    )
