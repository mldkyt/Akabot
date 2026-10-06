import datetime
import threading
from zoneinfo import ZoneInfo, available_timezones

from sqlalchemy import Connection

from database import engine
from utils.server_settings import ServerSetting, SettingType

setting_timezone = ServerSetting(
    name="Timezone", setting_type=SettingType.NORMAL, default="UTC"
)

# Per-guild timezone cache to avoid a database query on every call.
# Chat streaks, markov and other message handlers call "now" a lot.
_TTL_SECONDS = 300
_cache_lock = threading.Lock()
_cache: dict[int, tuple[str, float]] = {}


def is_valid_timezone(value: str) -> bool:
    return value in available_timezones()


def invalidate_timezone_cache(guild_id: int):
    """Drop the cached timezone for a guild (call after changing the setting)."""
    with _cache_lock:
        _cache.pop(guild_id, None)


def get_timezone(guild_id: int, c: Connection | None = None) -> str:
    """Return the IANA timezone name configured for a guild (defaults to UTC)."""
    now = datetime.datetime.now().timestamp()
    with _cache_lock:
        cached = _cache.get(guild_id)
        if cached is not None and now - cached[1] < _TTL_SECONDS:
            return cached[0]

    if c is not None:
        tz = setting_timezone.get(c, guild_id)
    else:
        with engine.begin() as _c:
            tz = setting_timezone.get(_c, guild_id)

    if not is_valid_timezone(tz):
        tz = "UTC"

    with _cache_lock:
        _cache[guild_id] = (tz, now)
    return tz


def get_now(guild_id: int, c: Connection | None = None) -> datetime.datetime:
    """Return the current time in the guild's timezone, as a naive datetime.

    The returned value is the guild's local wall-clock time (e.g. 00:00 for a
    Warsaw guild when it is midnight in Warsaw). It is naive because timestamps
    are stored in the database as naive datetimes, so existing SQL comparisons
    keep working. Summer time (DST) is handled automatically by zoneinfo.
    """
    tz = get_timezone(guild_id, c)
    return datetime.datetime.now(ZoneInfo(tz)).replace(tzinfo=None)