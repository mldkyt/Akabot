import logging

nekona_logger = logging.getLogger("nekona")
nekona_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

nekona_logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(filename="logs/nekona.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(nekona_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(nekona_formatter)

nekona_logger.addHandler(file_handler)
nekona_logger.addHandler(console_handler)