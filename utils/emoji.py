import re
import unicodedata

from discord import PartialEmoji

CUSTOM_EMOJI_RE = re.compile(r"<(a)?:([^:]+):(\d+)>")


def parse_emoji(emoji: str | None):
    if not emoji:
        return None

    match = CUSTOM_EMOJI_RE.fullmatch(emoji.strip())
    if match is not None:
        return PartialEmoji(
            name=match.group(2), id=int(match.group(3)), animated=bool(match.group(1))
        )

    return emoji


def normalize_emoji(emoji) -> str:
    """Return a stable string for comparing reactions with configured emojis."""
    value = str(emoji).strip()

    match = CUSTOM_EMOJI_RE.fullmatch(value)
    if match is not None:
        # The emoji ID is what identifies a custom emoji. Names can change and
        # users may type a different name, so only compare the ID.
        return f"custom:{match.group(3)}"

    return unicodedata.normalize("NFC", value).replace("\ufe0f", "").strip()
