from typing import Callable


class MessageAppend:
    def __init__(self, process: Callable[[int], str]):
        self.process = process
        pass


message_appends: list[MessageAppend] = []


def apply_appends(user_id: int, message: str):
    appended = ""

    for i in message_appends:
        appended += i.process(user_id) + "\n"

    if len(appended.strip()) > 0:
        return message + "\n\n" + appended

    return message
