from discord import Forbidden, HTTPException, Member
from sqlalchemy import select

from database import engine, roles_on_join
from logger import akabot_logger


async def apply_roles(member: Member):
    with engine.begin() as c:
        roles_ids = c.execute(
            select(roles_on_join.c.rid).where(roles_on_join.c.gid == str(member.guild.id))
        ).fetchall()
        roles = []

        for role_id in roles_ids:
            try:
                role = await member.guild.fetch_role(int(role_id[0]))
                roles.append(role)
            except HTTPException:
                akabot_logger.warning(
                    f"Failed to fetch role {role_id[0]} on join for {member} in guild {member.guild.id}"
                )

        try:
            await member.add_roles(*roles)
        except Forbidden:
            akabot_logger.warning(
                f"Forbidden to add roles on join for {member} in guild {member.guild.id}"
            )
        except Exception as e:
            akabot_logger.exception(f"Failed to apply roles on join for {member}: {e}")
