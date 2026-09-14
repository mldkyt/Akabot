from flask import Blueprint, render_template, request, session, flash, redirect
from sqlalchemy import select

from database import engine, giveaways, logging_channels, markov, message_counting_rewards, periodic_messages, premium_guilds, premium_tokens, sticky_messages, tags, temporary_vcs
from utils.anti_raid import setting_flood_enabled, setting_duplicate_enabled, setting_mentions_enabled, \
    setting_invite_enabled, setting_caps_enabled, setting_emoji_enabled, setting_sticker_enabled, \
    setting_joinburst_enabled, setting_mrbeast_scam
from utils.automod_actions import automod_actions
from utils.chat_revive import setting_chat_revive_channels
from utils.chat_summary import chat_summary
from utils.counting import setting_counting_channels
from utils.leveling import setting_leveling_rewards
from utils.moderation_commands import moderator_roles
from utils.premium import get_limit, generate_tokens, get_premium_context, is_owner, premium_enabled, redeem_token
from utils.roles_on_join import setting_roles_on_join
from utils.statistic_channels import setting_statistic_channels
from utils.suggestions import suggestion_channels
from utils.verification import setting_verification_role
from utils.welcome_goodbye import welcome_channel, goodbye_channel
from web.webutils.tokens import authorize, get_token_data

premium_bp = Blueprint("premium", __name__, template_folder="templates")


def get_usage(c, guild_id):
    usage = []

    usage.append({
        "name": "Counting channels",
        "usage": len(setting_counting_channels.get(c, guild_id)),
        "free_limit": 1,
    })
    usage.append({
        "name": "Leveling rewards",
        "usage": len(setting_leveling_rewards.get(c, guild_id)),
        "free_limit": 3,
    })
    usage.append({
        "name": "Moderator roles",
        "usage": len(moderator_roles.get(c, guild_id)),
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
        "usage": len(automod_actions.get(c, guild_id)),
        "free_limit": 3,
    })
    usage.append({
        "name": "Chat summary channels",
        "usage": len(chat_summary.get(c, guild_id)),
        "free_limit": 1,
    })
    usage.append({
        "name": "Roles on join",
        "usage": len(setting_roles_on_join.get(c, guild_id)),
        "free_limit": 3,
    })
    usage.append({
        "name": "Chat revive channels",
        "usage": len(setting_chat_revive_channels.get(c, guild_id)),
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
        "usage": len(setting_statistic_channels.get(c, guild_id)),
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
        "usage": len(suggestion_channels.get(c, guild_id)),
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
                select(premium_guilds.c.premium_until).where(
                    premium_guilds.c.gid == str(auth["guild"])
                )
            ).fetchone()
            if row is not None:
                until = row[0].strftime("%Y-%m-%d")

        if premium_context["enabled"]:
            usage = []
            for item in get_usage(c, auth["guild"]):
                limit = get_limit(c, auth["guild"], item["free_limit"])
                if limit is None:
                    text = f"{item['usage']}/unlimited"
                else:
                    text = f"{item['usage']}/{limit} ({round(item['usage'] / limit * 100)}%)"
                usage.append({"name": item["name"], "text": text})
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
                duration_days = 365 if request.form.get("duration") == "yearly" else 30

                prefix = request.form.get("format", "").strip().upper()
                if prefix == "":
                    prefix = "AKA"

                codes = generate_tokens(int(request.form["count"]), duration_days, prefix)
                flash(f"Generated {len(codes)} premium codes")

        tokens = [
            {
                "code": i[0],
                "duration_days": i[1],
                "redeemed_gid": i[2],
                "created_at": i[3].strftime("%Y-%m-%d") if i[3] is not None else "",
            }
            for i in c.execute(
                select(
                    premium_tokens.c.code,
                    premium_tokens.c.duration_days,
                    premium_tokens.c.redeemed_gid,
                    premium_tokens.c.created_at,
                ).order_by(premium_tokens.c.created_at.desc())
            ).fetchall()
        ]

    return render_template("premium_manage.html", tokens=tokens)