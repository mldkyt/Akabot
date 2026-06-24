from flask import Blueprint, session, render_template, request, flash, redirect
from sqlalchemy import select

from database import engine, synced_channels
from utils.counting import setting_counting_channels, any_count_mode, any_count_mode_count_words, \
    any_count_mode_count_frequency, any_count_mode_minimum_frequency, same_member_counting_mode
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

counting_bp = Blueprint("counting", __name__, template_folder='templates')

def set_settings(auth):
    if "channel" in request.form:
        return

    with engine.begin() as c:
        if request.form.get("any_count"):
            any_count_mode.set(c, auth["guild"], "true")
        else:
            any_count_mode.set(c, auth["guild"], "false")

        if request.form.get("count_words"):
            any_count_mode_count_words.set(c, auth["guild"], "true")
        else:
            any_count_mode_count_words.set(c, auth["guild"], "false")

        if request.form.get("count_word_frequency"):
            any_count_mode_count_frequency.set(c, auth["guild"], "true")
        else:
            any_count_mode_count_frequency.set(c, auth["guild"], "false")

        if request.form.get("same_member"):
            same_member_counting_mode.set(c, auth["guild"], "true")
        else:
            same_member_counting_mode.set(c, auth["guild"], "false")

        if "count_frequency_min" in request.form and request.form["count_frequency_min"].isnumeric():
            if 0 < int(request.form["count_frequency_min"]) < 100:
                any_count_mode_minimum_frequency.set(c, auth["guild"], request.form["count_frequency_min"])
            else:
                flash("Please set the count frequency minimum between 1 and 99")


def add_channel(auth):
    if "channel" in request.form and validate_text_channel_id(request.form["channel"]):
        with engine.begin() as c:
            if setting_counting_channels.is_in_list(c, auth["guild"], request.form["channel"]):
                flash("This channel is already added")
                return

            setting_counting_channels.add_to_list(c, auth["guild"], request.form["channel"])
            flash("Added channel successfully")

@counting_bp.route("/settings/counting", methods=["GET", "POST"])
def counting_index():
    authorization = authorize("/settings")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        set_settings(auth)
        add_channel(auth)

    with engine.begin() as c:
        counting_channel_ids = setting_counting_channels.get(c, auth["guild"])
        counting_channel_names = []
        for index in range(len(counting_channel_ids)):
            result = c.execute(
                select(synced_channels.c.cname)
                .where((synced_channels.c.gid == auth["guild"]) & (synced_channels.c.cid == counting_channel_ids[index]))
            ).fetchone()

            if result is not None:
                counting_channel_names.append({
                    "index": index,
                    "name": "#" + result[0]
                })

        text_channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.ctype == "text") & (synced_channels.c.gid == auth["guild"]))
        ).fetchall()]

        any_count = any_count_mode.get(c, auth["guild"]) == "true"
        count_words = any_count_mode_count_words.get(c, auth["guild"]) == "true"
        count_word_frequency = any_count_mode_count_frequency.get(c, auth["guild"]) == "true"
        count_frequency_min = any_count_mode_minimum_frequency.get(c, auth["guild"])
        same_member = same_member_counting_mode.get(c, auth["guild"]) == "true"

    return render_template("counting.html", counting_channels=counting_channel_names,
                           text_channels=text_channels, same_member=same_member,
                           any_count=any_count, count_words=count_words, count_word_frequency=count_word_frequency, count_frequency_min=count_frequency_min)

@counting_bp.route("/settings/counting/delete/<index>")
def counting_delete(index: str):
    authorization = authorize("/settings")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if not index.isnumeric():
        return redirect("/settings/counting", 302)

    with engine.begin() as c:
        chs = setting_counting_channels.get(c, auth["guild"])
        if len(chs) <= int(index):
            return redirect("/settings/counting", 302)

        chs = chs[int(index)]
        chs_parsed = c.execute(
            select(synced_channels.c.cname)
            .where((synced_channels.c.gid == auth["guild"]) & (synced_channels.c.cid == chs))
        ).fetchone()

        if "confirm" in request.args and request.args["confirm"] == "yes":
            setting_counting_channels.remove_from_list(c, auth["guild"], chs)
            return redirect("/settings/counting", 302)

    return render_template("counting_delete.html", channel=("#" + chs_parsed[0]) if chs_parsed is not None else chs)

