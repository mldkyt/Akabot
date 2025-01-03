#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 mldchan
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import datetime

from utils.languages import get_translation_for_key_localized as trl
from utils.tzutil import get_now_for_server


def pretty_time_delta(seconds: int | float, user_id: int, server_id: int, show_seconds=True, show_minutes=True) -> str:
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        # return trl(user_id, server_id, "pretty_time_delta_4").format(days=days, hours=hours, minutes=minutes,
        # seconds=seconds)
        if not show_minutes:
            return trl(user_id, server_id, "pretty_time_delta_4_no_minutes").format(days=days, hours=hours)
        elif not show_seconds:
            return trl(user_id, server_id, "pretty_time_delta_4_no_seconds").format(days=days, hours=hours,
                                                                                    minutes=minutes)
        else:
            return trl(user_id, server_id, "pretty_time_delta_4").format(days=days, hours=hours, minutes=minutes,
                                                                         seconds=seconds)
    elif hours > 0:
        # return trl(user_id, server_id, "pretty_time_delta_3").format(hours=hours, minutes=minutes, seconds=seconds)
        if not show_minutes:
            return trl(user_id, server_id, "pretty_time_delta_3_no_minutes").format(hours=hours)
        elif not show_seconds:
            return trl(user_id, server_id, "pretty_time_delta_3_no_seconds").format(hours=hours, minutes=minutes)
        else:
            return trl(user_id, server_id, "pretty_time_delta_3").format(hours=hours, minutes=minutes, seconds=seconds)
    elif minutes > 0:
        # return trl(user_id, server_id, "pretty_time_delta_2").format(minutes=minutes, seconds=seconds)
        if not show_minutes:
            return trl(user_id, server_id, "pretty_time_delta_less_than_an_hour")
        elif not show_seconds:
            return trl(user_id, server_id, "pretty_time_delta_2_no_seconds").format(minutes=minutes)
        else:
            return trl(user_id, server_id, "pretty_time_delta_2").format(minutes=minutes, seconds=seconds)
    else:
        if not show_minutes:
            return trl(user_id, server_id, "pretty_time_delta_less_than_an_hour")
        elif not show_seconds:
            return trl(user_id, server_id, "pretty_time_delta_less_than_a_minute")
        else:
            return trl(user_id, server_id, "pretty_time_delta_1").format(seconds=seconds)


def pretty_time(seconds_since_epoch: int | float) -> str:
    return datetime.datetime.fromtimestamp(seconds_since_epoch).strftime('%Y/%m/%d %H:%M:%S')


def get_date_time_str(guild_id: int) -> str:
    # format: yyyy/mm/dd hh:mm
    return get_now_for_server(guild_id).strftime('%Y/%m/%d %H:%M')
