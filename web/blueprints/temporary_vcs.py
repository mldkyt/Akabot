from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select

from database import engine, synced_channels, temporary_vc_creator_channels
from web.webutils.discord_sync import validate_voice_channel_id
from web.webutils.tokens import authorize, get_token_data

temporary_vcs_bp = Blueprint("temporary_vcs", __name__)


def handle_add(auth):
    with engine.begin() as c:
        if "channel" in request.form and validate_voice_channel_id(
                request.form["channel"]
        ):
            existing = c.execute(
                select(temporary_vc_creator_channels.c.cid).where(
                    (temporary_vc_creator_channels.c.gid == auth["guild"])
                    & (temporary_vc_creator_channels.c.cid == request.form["channel"])
                )
            ).fetchone()
            if existing is not None:
                flash("Already present")
                return

            c.execute(
                insert(temporary_vc_creator_channels).values(
                    gid=auth["guild"], cid=request.form["channel"]
                )
            )
            flash("Added temporary VC creator channel")


def handle_delete(auth):
    with engine.begin() as c:
        c.execute(
            delete(temporary_vc_creator_channels).where(
                (temporary_vc_creator_channels.c.gid == auth["guild"])
                & (temporary_vc_creator_channels.c.cid == request.args["delete"])
            )
        )


@temporary_vcs_bp.route("/settings/temporary_vcs", methods=["GET", "POST"])
def temporary_vcs_index():
    authorization = authorize("/settings/temporary_vcs")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_add(auth)

    if "delete" in request.args:
        handle_delete(auth)
        return redirect("/settings/temporary_vcs", 302)

    with engine.begin() as c:
        temporary_vcs_ids = [
            i[0]
            for i in c.execute(
                select(temporary_vc_creator_channels.c.cid)
                .where(temporary_vc_creator_channels.c.gid == auth["guild"])
                .order_by(temporary_vc_creator_channels.c.id)
            ).fetchall()
        ]
        temporary_vcs = []

        for i in range(len(temporary_vcs_ids)):
            name = c.execute(
                select(synced_channels.c.cname).where(
                    synced_channels.c.cid == temporary_vcs_ids[i]
                )
            ).fetchone()
            if name is None:
                flash(f"Failed to find channel {temporary_vcs_ids[i]}")
                continue

            temporary_vcs.append(
                {"index": i, "id": temporary_vcs_ids[i], "name": name[0]}
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
        "temporary_vcs.html", temporary_vcs=temporary_vcs, channels=channels
    )
