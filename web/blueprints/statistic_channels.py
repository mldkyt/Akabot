from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select

from database import engine, statistic_channels, synced_channels
from web.webutils.discord_sync import validate_voice_channel_id
from web.webutils.tokens import authorize, get_token_data

statistic_channels_bp = Blueprint("statistic_channels", __name__)


def handle_post(auth, is_edit: bool = False):
    if "channel" not in request.form or "template" not in request.form:
        return
    if not validate_voice_channel_id(request.form["channel"]):
        flash("Invalid voice channel selected")
        return
    if not 2 <= len(request.form["template"]) <= 50:
        flash("Template too short or too long, keep it between 2 and 50 characters")
        return
    if ";" in request.form["template"]:
        flash("The template must not have semicolons")
        return

    with engine.begin() as c:
        existing = c.execute(
            select(statistic_channels.c.cid).where(
                (statistic_channels.c.gid == auth["guild"])
                & (statistic_channels.c.cid == request.form["channel"])
            )
        ).fetchone()
        if existing is not None:
            flash("This ID already has a template assigned, please edit instead!")
            return

        c.execute(
            insert(statistic_channels).values(
                gid=auth["guild"],
                cid=request.form["channel"],
                template=request.form["template"],
            )
        )


def handle_delete(auth):
    with engine.begin() as c:
        c.execute(
            delete(statistic_channels).where(
                (statistic_channels.c.gid == auth["guild"])
                & (statistic_channels.c.cid == request.args["delete"])
            )
        )


@statistic_channels_bp.route("/settings/statistic_channels", methods=["GET", "POST"])
def statistic_channels_index():
    authorization = authorize("/settings/statistic_channels")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_post(auth)

    if "delete" in request.args:
        handle_delete(auth)
        return redirect("/settings/statistic_channels", 303)

    with engine.begin() as c:
        statistic_channels_rows = c.execute(
            select(statistic_channels.c.cid, statistic_channels.c.template)
            .where(statistic_channels.c.gid == auth["guild"])
            .order_by(statistic_channels.c.id)
        ).fetchall()
        statistic_channels_list = []
        for i in range(len(statistic_channels_rows)):
            args = statistic_channels_rows[i]
            channel_name = c.execute(
                select(synced_channels.c.cname).where(
                    (synced_channels.c.cid == args[0])
                    & (synced_channels.c.gid == auth["guild"])
                )
            ).fetchone()

            if channel_name is None:
                continue

            statistic_channels_list.append(
                {
                    "index": i,
                    "id": args[0],
                    "name": channel_name[0],
                    "template": args[1],
                }
            )

        channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == auth["guild"])
                    & (synced_channels.c.ctype == "voice")
                )
            ).fetchall()
        ]

    return render_template(
        "statistic_channels.html",
        statistic_channels=statistic_channels_list,
        channels=channels,
    )


@statistic_channels_bp.route(
    "/settings/statistic_channels/edit/<index>", methods=["POST"]
)
def statistic_channels_edit(index: str):
    authorization = authorize("/settings/statistic_channels")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if not index.isnumeric():
        return redirect("/settings/statistic_channels", 303)

    with engine.begin() as c:
        rows = c.execute(
            select(statistic_channels.c.cid)
            .where(statistic_channels.c.gid == auth["guild"])
            .order_by(statistic_channels.c.id)
        ).fetchall()
        if len(rows) <= int(index):
            return redirect("/settings/statistic_channels", 303)

        c.execute(
            delete(statistic_channels).where(
                (statistic_channels.c.gid == auth["guild"])
                & (statistic_channels.c.cid == rows[int(index)][0])
            )
        )

    handle_post(auth, is_edit=True)
    return redirect("/settings/statistic_channels", 303)
