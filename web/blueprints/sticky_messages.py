from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, sticky_messages, synced_channels
from web.webutils.tokens import authorize, get_token_data

sticky_messages_bp = Blueprint("sticky_messages", __name__, template_folder="templates")


def _channel_is_valid(c, guild, channel_id):
    return (
        c.execute(
            select(synced_channels.c.cid).where(
                (synced_channels.c.gid == guild)
                & (synced_channels.c.cid == channel_id)
                & (synced_channels.c.ctype == "text")
            )
        ).fetchone()
        is not None
    )


@sticky_messages_bp.route("/settings/sticky_messages", methods=["GET", "POST"])
def sticky_messages_index():
    authorization = authorize("/settings/sticky_messages")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        action = request.form.get("action", "create")
        channel = request.form.get("channel", "")
        content = request.form.get("content", "")
        old_channel = request.form.get("id", "")

        with engine.begin() as c:
            if action == "delete":
                if old_channel:
                    c.execute(
                        delete(sticky_messages).where(
                            (sticky_messages.c.channel_id == old_channel)
                            & (sticky_messages.c.guild_id == auth["guild"])
                        )
                    )
                    flash("Deleted sticky message")
            elif not channel or not content:
                flash("Please choose a channel and write a message")
            elif not _channel_is_valid(c, auth["guild"], channel):
                flash("Unknown channel")
            else:
                conflict = c.execute(
                    select(sticky_messages.c.channel_id).where(
                        (sticky_messages.c.channel_id == channel)
                        & (sticky_messages.c.guild_id == auth["guild"])
                    )
                ).fetchone()
                if conflict is not None and channel != old_channel:
                    flash("That channel already has a sticky message")
                elif action == "update" and old_channel:
                    c.execute(
                        update(sticky_messages)
                        .values(channel_id=channel, content=content)
                        .where(
                            (sticky_messages.c.channel_id == old_channel)
                            & (sticky_messages.c.guild_id == auth["guild"])
                        )
                    )
                    flash("Saved sticky message")
                else:
                    c.execute(
                        insert(sticky_messages).values(
                            channel_id=channel,
                            content=content,
                            guild_id=auth["guild"],
                        )
                    )
                    flash("Added sticky message")

        return redirect(
            f"/settings/sticky_messages?tab={request.form.get('_tab', 'messages')}",
            303,
        )

    active_tab = request.args.get("tab", "messages")
    if active_tab not in {"messages", "create"}:
        active_tab = "messages"

    with engine.begin() as c:
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
                select(synced_channels.c.cname).where(
                    (synced_channels.c.cid == i[0])
                    & (synced_channels.c.gid == auth["guild"])
                )
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
        active_tab=active_tab,
    )
