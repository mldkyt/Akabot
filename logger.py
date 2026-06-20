import logging
import os.path

akabot_logger = logging.getLogger("akabot")
akabot_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

akabot_logger.setLevel(logging.DEBUG)

if not os.path.exists("logs"):
    os.mkdir("logs")

file_handler = logging.FileHandler(filename="logs/akabot.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(akabot_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(akabot_formatter)

akabot_logger.addHandler(file_handler)
akabot_logger.addHandler(console_handler)
