from flask import Blueprint, render_template, request, session, flash, redirect
from sqlalchemy import select

from database import engine, giveaways, logging_channels, markov, message_counting_rewards, periodic_messages, premium_guilds, premium_tokens, reaction_roles, sticky_messages, tags, temporary_vcs, chat_revive_channels, chat_summary_channels, counting_channels, leveling_rewards, moderator_roles, roles_on_join, statistic_channels, suggestion_channels, automod_actions
from utils.anti_raid import setting_flood_enabled, setting_duplicate_enabled, setting_mentions_enabled, \
    setting_invite_enabled, setting_caps_enabled, setting_emoji_enabled, setting_sticker_enabled, \
    setting_joinburst_enabled, setting_mrbeast_scam
from utils.premium import generate_tokens, get_premium_context, is_owner, redeem_token, usage_bar
from utils.verification import setting_verification_role
from utils.welcome_goodbye import welcome_channel, goodbye_channel
from web.webutils.tokens import authorize, get_token_data

premium_bp = Blueprint("premium", __name__, template_folder="templates")


def get_usage(c, guild_id):
    usage = []

    usage.append({
        "name": "Counting channels",
        "usage": len(c.execute(
            select(counting_channels.c.cid).where(counting_channels.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 1,
    })
    usage.append({
        "name": "Leveling rewards",
        "usage": len(c.execute(
            select(leveling_rewards.c.id).where(leveling_rewards.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 3,
    })
    usage.append({
        "name": "Moderator roles",
        "usage": len(c.execute(
            select(moderator_roles.c.rid).where(moderator_roles.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 5,
    })
    usage.append({
        "name": "Welcome messages",
        "usage": 1 if welcome_channel.get(c, guild_id) != "" else 0,
        "free_limit": 1,
    })
    usage.append({
        "name": "Goodbye messages",
        "usage": 1 if goodbye_channel.get(c, guild_id) != "" else 0,
        "free_limit": 1,
    })
    usage.append({
        "name": "Logging channels",
        "usage": len(c.execute(
            select(logging_channels.c.cid).where(logging_channels.c.gid == str(guild_id))
            .group_by(logging_channels.c.cid)
        ).fetchall()),
        "free_limit": 1,
    })
    usage.append({
        "name": "Automod actions",
        "usage": len(c.execute(
            select(automod_actions.c.id).where(automod_actions.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 3,
    })
    usage.append({
        "name": "Chat summary channels",
        "usage": len(c.execute(
            select(chat_summary_channels.c.cid).where(chat_summary_channels.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 1,
    })
    usage.append({
        "name": "Roles on join",
        "usage": len(c.execute(
            select(roles_on_join.c.rid).where(roles_on_join.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 3,
    })
    usage.append({
        "name": "Chat revive channels",
        "usage": len(c.execute(
            select(chat_revive_channels.c.id).where(chat_revive_channels.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 1,
    })
    usage.append({
        "name": "Temporary voice channels",
        "usage": len(c.execute(
            select(temporary_vcs.c.cid).where(temporary_vcs.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 3,
    })
    usage.append({
        "name": "Statistic channels",
        "usage": len(c.execute(
            select(statistic_channels.c.cid).where(statistic_channels.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 2,
    })
    usage.append({
        "name": "Verification setups",
        "usage": 1 if setting_verification_role.get(c, guild_id) != "" else 0,
        "free_limit": 1,
    })
    enabled_detectors = 0
    for setting in (setting_flood_enabled, setting_duplicate_enabled, setting_mentions_enabled,
                    setting_invite_enabled, setting_caps_enabled, setting_emoji_enabled,
                    setting_sticker_enabled, setting_joinburst_enabled):
        if setting.get(c, guild_id) == "true":
            enabled_detectors += 1
    if setting_mrbeast_scam.get(c, guild_id) == "true":
        enabled_detectors += 1
    usage.append({
        "name": "Anti raid protections",
        "usage": enabled_detectors,
        "free_limit": 3,
    })
    usage.append({
        "name": "Active giveaways",
        "usage": len(c.execute(
            select(giveaways.c.id).where(
                (giveaways.c.gid == str(guild_id)) & (giveaways.c.end.is_not(None))
            )
        ).fetchall()),
        "free_limit": 1,
    })
    usage.append({
        "name": "Message counting rewards",
        "usage": len(c.execute(
            select(message_counting_rewards.c.id).where(message_counting_rewards.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 3,
    })
    usage.append({
        "name": "Periodic messages",
        "usage": len(c.execute(
            select(periodic_messages.c.id).where(periodic_messages.c.guild_id == str(guild_id))
        ).fetchall()),
        "free_limit": 2,
    })
    usage.append({
        "name": "Sticky messages",
        "usage": len(c.execute(
            select(sticky_messages.c.channel_id).where(sticky_messages.c.guild_id == str(guild_id))
        ).fetchall()),
        "free_limit": 1,
    })
    usage.append({
        "name": "Suggestion channels",
        "usage": len(c.execute(
            select(suggestion_channels.c.cid).where(suggestion_channels.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 1,
    })
    usage.append({
        "name": "Tags",
        "usage": len(c.execute(
            select(tags.c.id).where(tags.c.guild_id == str(guild_id))
        ).fetchall()),
        "free_limit": 3,
    })
    usage.append({
        "name": "Markov channels",
        "usage": len(c.execute(
            select(markov.c.channel_id).where(markov.c.guild_id == str(guild_id))
        ).fetchall()),
        "free_limit": 1,
    })
    usage.append({
        "name": "Reaction role messages",
        "usage": len(c.execute(
            select(reaction_roles.c.id).where(reaction_roles.c.gid == str(guild_id))
        ).fetchall()),
        "free_limit": 3,
    })

    return usage


@premium_bp.route("/settings/premium", methods=["GET", "POST"])
def premium_index():
    authorization = authorize("/settings/premium")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    context = {}
    with engine.begin() as c:
        premium_context = get_premium_context(c, auth["guild"])

        if request.method == "POST":
            if "code" in request.form:
                ok, message = redeem_token(c, auth["guild"], request.form["code"])
                if ok:
                    flash(f"Premium activated until {message}!")
                    premium_context = get_premium_context(c, auth["guild"])
                else:
                    flash(f"Could not activate premium: {message}")

        until = None
        if premium_context["active"]:
            row = c.execute(
                select(premium_guilds.c.premium_until, premium_guilds.c.unlimited).where(
                    premium_guilds.c.gid == str(auth["guild"])
                )
            ).fetchone()
            if row is not None:
                until = "unlimited" if row[1] else row[0].strftime("%Y-%m-%d")

        if premium_context["enabled"]:
            usage = []
            for item in get_usage(c, auth["guild"]):
                bar = usage_bar(c, auth["guild"], item["name"], item["usage"], item["free_limit"])
                if bar is not None:
                    usage.append(bar)
        else:
            usage = []

        owner = is_owner(auth["user"])
        context = {
            "premium": premium_context,
            "usage": usage,
            "owner": owner,
            "until": until,
        }

    return render_template("premium.html", **context)


@premium_bp.route("/settings/premium/manage", methods=["GET", "POST"])
def premium_manage():
    authorization = authorize("/settings/premium/manage")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if not is_owner(auth["user"]):
        return redirect("/settings/premium")

    with engine.begin() as c:
        if request.method == "POST":
            if "count" in request.form and request.form["count"].isnumeric():
                duration = request.form.get("duration")
                unlimited = duration == "unlimited"
                duration_days = 365 if duration == "yearly" else (30 if duration == "monthly" else 0)

                prefix = request.form.get("format", "").strip().upper()
                if prefix == "":
                    prefix = "AKA"

                codes = generate_tokens(int(request.form["count"]), duration_days, prefix, unlimited=unlimited)
                flash(f"Generated {len(codes)} premium codes")

        tokens = [
            {
                "code": i[0],
                "duration_days": i[1],
                "unlimited": i[2],
                "redeemed_gid": i[3],
                "created_at": i[4].strftime("%Y-%m-%d") if i[4] is not None else "",
            }
            for i in c.execute(
                select(
                    premium_tokens.c.code,
                    premium_tokens.c.duration_days,
                    premium_tokens.c.unlimited,
                    premium_tokens.c.redeemed_gid,
                    premium_tokens.c.created_at,
                ).order_by(premium_tokens.c.created_at.desc())
            ).fetchall()
        ]

    return render_template("premium_manage.html", tokens=tokens)