import random
import re

from discord import Message

from database import engine
from utils.server_settings import ServerSetting, SettingType, setting_to_boolean, setting_simple_string_boolean

meowing = ServerSetting(
    name="Meow back at messages",
    setting_type=SettingType.NORMAL,
    default="false",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("%s meowing at messages (cat)", "Enabled", "Disabled"),
    normal_view=setting_simple_string_boolean("Meowing back at messages is %s", "enabled", "disabled")
)

wafing = ServerSetting(
    name="Waf back at messages",
    setting_type=SettingType.NORMAL,
    default="false",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("%s waffing at messages (fox)", "Enabled", "Disabled"),
    normal_view=setting_simple_string_boolean("Waffing back at messages is %s", "enabled", "disabled")
)

barking = ServerSetting(
    name="Bark back at messages",
    setting_type=SettingType.NORMAL,
    default="false",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("%s barking at messages (dog)", "Enabled", "Disabled"),
    normal_view=setting_simple_string_boolean("Barking back at messages is %s", "enabled", "disabled")
)

colon_3 = ServerSetting(
    name=":3 back at messages",
    setting_type=SettingType.NORMAL,
    default="false",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("%s :3ing at messages (owo)", "Enabled", "Disabled"),
    normal_view=setting_simple_string_boolean(":3ing back at messages is %s", "enabled", "disabled")
)

owo = ServerSetting(
    name="OwO back at messages",
    setting_type=SettingType.NORMAL,
    default="false",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("%s OwOing back at messages (owo)", "Enabled", "Disabled"),
    normal_view=setting_simple_string_boolean("OwOing back at messages is %s", "enabled", "disabled")
)

awawa = ServerSetting(
    name="awawa back at messages",
    setting_type=SettingType.NORMAL,
    default="false",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("%s awawaing back at messages (awawa)", "Enabled", "Disabled"),
    normal_view=setting_simple_string_boolean("awawaing back at messages is %s", "enabled", "disabled")
)


def handle_colon_three(message: Message):
    # count :3 in message
    count = 0
    for i in re.finditer(r":(3+)", message.content.lower()):
        count = count + len(i[1])

    if count == 0:
        return ""

    return ":3 " * count


def generate_meow():
    meow = random.choice(["meow", "nya", "mraow", "mwrmmwra"])

    if meow == "nya":
        return "ny" + random.randint(1, 8) * "a"
    elif meow == "mwrmmwra":
        meow = "mr"
        for i in range(random.randint(4, 12)):
            meow += random.choice(["a", "w", "r"])

        return meow

    return meow


def handle_meow(message: Message):
    # count meows
    count = 0

    for i in message.content.split(" "):
        count += len(re.findall(r"(^m[mraeowp]{3,}$|^nya+$)", i.lower()))

    if count == 0:
        return ""

    return " ".join([generate_meow() for _ in range(count)]) + " :3"


def generate_woof():
    a = random.choice([0, 1])

    if a == 0:
        is_a = random.choice([0, 1])

        return ("a" if is_a else "") + "wru" + "f" * random.randint(1, 3)
    elif a == 1:
        return "woof"
    else:
        return "waf"


def handle_woof(message: Message):
    # count woofs
    count = 0

    for i in message.content.split(" "):
        count += len(re.findall(r"^([awruf]?[wruf]{3,})$", i.lower()))

    if count == 0:
        return ""

    return " ".join([generate_woof() for _ in range(count)])


def handle_waf(message: Message):
    count = 0

    for i in message.content.split(" "):
        if i.lower() == "waf":
            count += 1

    if count == 0:
        return ""

    return " ".join(["waf" for _ in range(count)])


def handle_owo(message: Message):
    # count OwOs and UwUs
    count = len(re.findall(r"([ou>]w[<ou])", message.content.lower()))

    if count == 0:
        return ""

    return (
            " ".join(random.choices(["OwO", "owo", "UwU", "uwu", ">w<"], k=count)) + " :3"
    )


def handle_awawa(message: Message):
    count_awawa = 0

    for i in message.content.split(" "):
        if i.startswith("awa"):
            count_awawa += (len(i) - 3) // 2

    resp = "awa" + "wa" * count_awawa

    if count_awawa == 0:
        return ""

    return resp.strip()


def meow_back_for_message(message: Message):
    if message.guild is None:
        return ""

    with engine.begin() as c:
        meowing_enabled = meowing.get_guild(c, message.guild) == "true"
        colon_3_enabled = colon_3.get_guild(c, message.guild) == "true"
        owo_enabled = owo.get_guild(c, message.guild) == "true"
        awawa_enabled = awawa.get_guild(c, message.guild) == "true"
        barking_enabled = barking.get_guild(c, message.guild) == "true"
        wafing_enabled = wafing.get_guild(c, message.guild) == "true"

    message_reply = " ".join(
        [
            handle_meow(message) if meowing_enabled else "",
            handle_colon_three(message) if colon_3_enabled else "",
            handle_owo(message) if owo_enabled else "",
            handle_awawa(message) if awawa_enabled else "",
            handle_woof(message) if barking_enabled else "",
            handle_waf(message) if wafing_enabled else "",
        ]
    )

    print(message_reply)

    return message_reply.strip()
