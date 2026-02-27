from discord import Cog, Bot, VoiceState, Member

from utils.docs import Docs, DocsSetting
from utils.server_settings import settings, SettingType
from utils.temporary_vc import handle_voice_update, setting_temporary_vcs


class TemporaryVC(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState,
                                    after: VoiceState):
        await handle_voice_update(member, before, after)


def setup(bot: Bot):
    bot.add_cog(TemporaryVC(bot))

    settings.add_setting(setting_temporary_vcs)


def docs():
    return Docs(
        name="Temporary VC",
        description="Temporary voice channels.",
        settings=[
            DocsSetting(
                name="Temporary VCs",
                description="List of temporary voice channels.",
                add_description="Name or ID of a voice chat. Discord won't autocomplete mentions of voice chats for some reason.",
                remove_description="Name or ID of a voice chat. Discord won't autocomplete mentions of voice chats for some reason.",
                setting_type=SettingType.LIST
            )
        ]
    )
