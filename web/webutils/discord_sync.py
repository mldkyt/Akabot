from sqlalchemy import select

from database import engine, synced_channels, synced_roles, synced_automod_rules


def validate_text_channel_id(channel_id: str):
    with engine.begin() as c:
        return c.execute(
            select(synced_channels)
            .where((synced_channels.c.cid == channel_id) & (synced_channels.c.ctype == "text"))
        ).fetchone() is not None


def validate_voice_channel_id(channel_id: str):
    with engine.begin() as c:
        return c.execute(
            select(synced_channels)
            .where((synced_channels.c.cid == channel_id) & (synced_channels.c.ctype == "voice"))
        ).fetchone() is not None


def validate_role_id(role_id: str):
    with engine.begin() as c:
        return c.execute(
            select(synced_roles)
            .where(synced_roles.c.rid == role_id)
        ).fetchone() is not None


def validate_automod_rule_id(automod_rule_id: str):
    with engine.begin() as c:
        return c.execute(
            select(synced_automod_rules)
            .where(synced_automod_rules.c.aid == automod_rule_id)
        ).fetchone() is not None
